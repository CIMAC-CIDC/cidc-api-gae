"""Clean up empty additional_metadata

Revision ID: 14a807e0e6e8
Revises: f50c611727ca
Create Date: 2020-10-07 11:54:11.993039

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "14a807e0e6e8"
down_revision = "f50c611727ca"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE downloadable_files SET additional_metadata = '{}'::jsonb WHERE additional_metadata is null or additional_metadata = 'null'"
    )
    op.alter_column(
        "downloadable_files",
        "additional_metadata",
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("downloadable_files", "additional_metadata", nullable=True)
    # ### end Alembic commands ###
