"""empty message

Revision ID: ff3141aecdd4
Revises: b8eaf567ac2f
Create Date: 2019-11-14 11:43:49.297901

"""
from typing import Callable

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm.session import Session
from google.cloud import storage

from cidc_schemas.migrations import v0_10_0_to_v0_10_2, MigrationResult
from cidc_api.models import TrialMetadata, DownloadableFiles
from cidc_api.config.settings import GOOGLE_DATA_BUCKET

# revision identifiers, used by Alembic.
revision = "ff3141aecdd4"
down_revision = "b8eaf567ac2f"
branch_labels = None
depends_on = None

session = Session(bind=op.get_bind())
storage_client = storage.Client()


def _do_metadata_migration(metadata_migration: Callable[[dict], MigrationResult]):
    """Migrate trial metadata and downloadable files according to metadata_migration"""
    trials = session.query(TrialMetadata).with_for_update().all()

    for trial in trials:
        migration = metadata_migration(trial.metadata_json)

        # Update the trial metadata object
        trial.metadata_json = migration.result

        # Update the relevant downloadable files and GCS objects
        for old_gcs_uri, artifact in migration.file_updates.items():
            # Update the downloadable file associated with this blob
            df = (
                session.query(DownloadableFiles)
                .filter_by(object_url=old_gcs_uri)
                .with_for_update()
                .one()
            )
            for column, value in artifact.items():
                if hasattr(df, column):
                    setattr(df, column, value)

            # If the GCS URI has changed, rename the blob
            new_gcs_uri = artifact["object_url"]
            if old_gcs_uri != new_gcs_uri:
                bucket = storage_client.get_bucket(GOOGLE_DATA_BUCKET)
                old_blob = bucket.blob(old_gcs_uri)
                new_blob = bucket.rename_blob(old_blob, new_gcs_uri)

    session.commit()


def upgrade():
    """Update Olink's assay_raw_ct artifact data format to CSV"""
    _do_metadata_migration(v0_10_0_to_v0_10_2.upgrade)


def downgrade():
    """Downgrade Olink's assay_raw_ct artifact data format to XLSX"""
    _do_metadata_migration(v0_10_0_to_v0_10_2.downgrade)
