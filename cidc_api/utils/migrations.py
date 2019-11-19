import os
from contextlib import contextmanager
from typing import Callable, List, NamedTuple

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm.session import Session
from google.cloud import storage

from cidc_api.models import (
    TrialMetadata,
    DownloadableFiles,
    AssayUploads,
    AssayUploadStatus,
    ManifestUploads,
)
from cidc_api.config.settings import GOOGLE_DATA_BUCKET, GOOGLE_UPLOAD_BUCKET
from cidc_schemas.migrations import MigrationResult
from cidc_schemas.prism import _get_uuid_info


class PieceOfWork(NamedTuple):
    do: Callable[[], None]
    undo: Callable[[], None]


class RollbackableQueue:
    """A collection of reversible pieces-of-work."""

    def __init__(self):
        self.tasks = []

    def schedule(self, task: PieceOfWork):
        """Add a task to the task queue."""
        self.tasks.append(task)

    def run_all(self):
        """
        Attempt to run all tasks in the queue, rolling back
        successfully completed tasks if a subsequent task fails.
        """
        for i, task in enumerate(self.tasks):
            try:
                task.do()
            except:
                for done_task in self.tasks[:i]:
                    done_task.undo()
                raise


@contextmanager
def migration_session():
    session = Session(bind=op.get_bind())

    try:
        yield session
    except:
        session.rollback()
        raise
    finally:
        session.commit()


def run_metadata_migration(metadata_migration: Callable[[dict], MigrationResult]):
    """Migrate trial metadata, upload job patches, and downloadable files according to `metadata_migration`"""
    with migration_session() as session:
        _run_metadata_migration(metadata_migration, session)


def _run_metadata_migration(
    metadata_migration: Callable[[dict], MigrationResult], session: Session
):
    # Initialize an empty list of pieces of work to do on GCS resources
    gcs_tasks = RollbackableQueue()

    # Migrate all trial records
    trials: List[TrialMetadata] = session.query(TrialMetadata).with_for_update().all()
    for trial in trials:
        migration = metadata_migration(trial.metadata_json)

        # Update the trial metadata object
        trial.metadata_json = migration.result

        # Update the relevant downloadable files and GCS objects
        for old_gcs_uri, artifact in migration.file_updates.items():
            # Update the downloadable file associated with this blob
            df: DownloadableFiles = (
                session.query(DownloadableFiles)
                .filter_by(object_url=old_gcs_uri)
                .with_for_update()
                .one()
            )
            for column, value in artifact.items():
                if hasattr(df, column):
                    setattr(df, column, value)

            # Regenerate additional metadata from the migrated clinical trial
            # metadata object.
            df.additional_metadata = _get_uuid_info(
                migration.result, artifact["upload_placeholder"]
            )[1]

            # If the GCS URI has changed, rename the blob
            new_gcs_uri = artifact["object_url"]
            if old_gcs_uri != new_gcs_uri:
                renamer = PieceOfWork(
                    lambda: rename_gcs_blob(
                        GOOGLE_DATA_BUCKET, old_gcs_uri, new_gcs_uri
                    ),
                    lambda: rename_gcs_blob(
                        GOOGLE_DATA_BUCKET, new_gcs_uri, old_gcs_uri
                    ),
                )
                gcs_tasks.schedule(renamer)

    # Migrate all assay upload successes
    successful_assay_uploads: List[AssayUploads] = session.query(
        AssayUploads
    ).filter_by(status=AssayUploadStatus.MERGE_COMPLETED.value).with_for_update().all()
    for upload in successful_assay_uploads:
        migration = metadata_migration(upload.assay_patch)

        # Update the metadata patch
        upload.assay_patch = migration.result

        # Update the GCS URIs of files that were part of this upload
        old_file_map = upload.gcs_file_map
        new_file_map = {}
        for (
            old_upload_uri,
            old_target_uri,
            artifact_uuid,
        ) in upload.upload_uris_with_data_uris_with_uuids():
            upload_timestamp = old_upload_uri[len(old_target_uri) + 1 :]
            if old_target_uri in migration.file_updates:
                new_target_uri = migration.file_updates[old_target_uri]["object_url"]
                if old_gcs_uri != new_target_uri:
                    new_upload_uri = "/".join([new_target_uri, upload_timestamp])
                    renamer = PieceOfWork(
                        lambda: rename_gcs_blob(
                            GOOGLE_UPLOAD_BUCKET, old_upload_uri, new_upload_uri
                        ),
                        lambda: rename_gcs_blob(
                            GOOGLE_UPLOAD_BUCKET, new_upload_uri, old_upload_uri
                        ),
                    )
                    gcs_tasks.schedule(renamer)
                new_file_map[new_upload_uri] = artifact_uuid

        # Update the upload's file map to use new GCS URIs
        upload.gcs_file_map = new_file_map

    # Migrate all manifest records
    manifest_uploads: List[ManifestUploads] = session.query(
        ManifestUploads
    ).with_for_update().all()
    for upload in manifest_uploads:
        migration = metadata_migration(upload.metadata_patch)

        # Update the metadata patch
        upload.metadata_patch = migration.result

    # Attempt to make GCS updates
    gcs_tasks.run_all()


is_testing = os.environ.get("TESTING")


def rename_gcs_blob(bucket, old_name, new_name):
    if is_testing:
        return

    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket)
    old_blob = bucket.blob(old_name)
    new_blob = bucket.rename_blob(old_blob, new_name)
    return new_blob
