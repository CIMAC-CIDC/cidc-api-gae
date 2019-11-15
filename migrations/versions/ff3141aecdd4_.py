"""Update Olink's assay_raw_ct artifact data format from XLSX to CSV.

Revision ID: ff3141aecdd4
Revises: b8eaf567ac2f
Create Date: 2019-11-14 11:43:49.297901

"""
import os

from cidc_schemas.migrations import v0_10_0_to_v0_10_2

from cidc_api.migration_utils import run_metadata_migration

# revision identifiers, used by Alembic.
revision = "ff3141aecdd4"
down_revision = "b8eaf567ac2f"
branch_labels = None
depends_on = None

is_testing = os.environ.get("TESTING")


def upgrade():
    """Update Olink's assay_raw_ct artifact data format to CSV"""
    # Don't run this migration on the test database
    if is_testing:
        return

    run_metadata_migration(v0_10_0_to_v0_10_2.upgrade)


def downgrade():
    """Downgrade Olink's assay_raw_ct artifact data format to XLSX"""
    # Don't run this migration on the test database
    if is_testing:
        return

    run_metadata_migration(v0_10_0_to_v0_10_2.downgrade)
