"""empty message

Revision ID: b8eaf567ac2f
Revises: aa8a94b8e115
Create Date: 2019-10-07 12:11:17.836062

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b8eaf567ac2f"
down_revision = "aa8a94b8e115"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "downloadable_files",
        sa.Column(
            "additional_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("downloadable_files", "additional_metadata")
    # ### end Alembic commands ###
