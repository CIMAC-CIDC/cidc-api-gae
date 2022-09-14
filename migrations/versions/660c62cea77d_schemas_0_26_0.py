"""schemas_0_26_0

Revision ID: 660c62cea77d
Revises: af08550a6fef
Create Date: 2022-09-09 17:41:52.159401

"""
from cidc_schemas.migrations import v0_25_54_to_v0_26_0

from cidc_api.models.migrations import run_metadata_migration


# revision identifiers, used by Alembic.
revision = '660c62cea77d'
down_revision = 'af08550a6fef'
branch_labels = None
depends_on = None


def upgrade():
    run_metadata_migration(v0_25_54_to_v0_26_0.upgrade, False)


def downgrade():
    run_metadata_migration(v0_25_54_to_v0_26_0.downgrade, False)
