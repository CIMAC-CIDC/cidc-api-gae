import os
from typing import Callable

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm.session import Session
from google.cloud import storage

from cidc_api.models import TrialMetadata, DownloadableFiles
from cidc_api.config.settings import GOOGLE_DATA_BUCKET
from cidc_schemas.migrations import MigrationResult
from cidc_schemas.prism import _get_uuid_info


def run_metadata_migration(metadata_migration: Callable[[dict], MigrationResult]):
    """Migrate trial metadata, upload job patches, and downloadable files according to `metadata_migration`"""
    session = Session(bind=op.get_bind())

    trials = session.query(TrialMetadata).with_for_update().all()

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
                rename_gcs_blob(GOOGLE_DATA_BUCKET, old_gcs_uri, new_gcs_uri)

    session.commit()


is_testing = os.environ.get("TESTING")


def rename_gcs_blob(bucket, old_name, new_name):
    storage_client = storage.Client() if not is_testing else None
    bucket = storage_client.get_bucket(bucket)
    old_blob = bucket.blob(old_name)
    new_blob = bucket.rename_blob(old_blob, new_name)
    return new_blob
