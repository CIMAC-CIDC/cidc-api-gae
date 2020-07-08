"""empty message

Revision ID: 4fc2addf0090
Revises: 37436458bc78
Create Date: 2020-07-08 13:32:46.052098

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4fc2addf0090"
down_revision = "37436458bc78"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("upload_jobs", sa.Column("token", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("upload_jobs", "token")
    # ### end Alembic commands ###