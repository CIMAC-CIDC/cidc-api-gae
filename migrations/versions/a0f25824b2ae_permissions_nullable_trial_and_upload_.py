"""permissions nullable trial and upload type

Revision ID: a0f25824b2ae
Revises: 7d3ad965db30
Create Date: 2021-04-20 14:57:14.708607

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a0f25824b2ae"
down_revision = "7d3ad965db30"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "permissions", "trial_id", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "permissions", "upload_type", existing_type=sa.VARCHAR(), nullable=True
    )
    op.create_check_constraint(
        "ck_nonnull_trial_id_or_upload_type",
        "permissions",
        "trial_id is not null or upload_type is not null",
    )


def downgrade():
    op.drop_constraint("ck_nonnull_trial_id_or_upload_type", "permissions")
    op.alter_column(
        "permissions", "upload_type", existing_type=sa.VARCHAR(), nullable=False
    )
    op.alter_column(
        "permissions", "trial_id", existing_type=sa.VARCHAR(), nullable=False
    )
