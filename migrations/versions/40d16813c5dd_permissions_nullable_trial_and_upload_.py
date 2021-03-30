"""permissions nullable trial and upload type

Revision ID: 40d16813c5dd
Revises: 509970372467
Create Date: 2021-03-29 12:08:35.146241

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "40d16813c5dd"
down_revision = "509970372467"
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
