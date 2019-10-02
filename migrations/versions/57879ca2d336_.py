"""empty message

Revision ID: 57879ca2d336
Revises: 571d8a2570a6
Create Date: 2019-09-23 12:34:33.046608

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '57879ca2d336'
down_revision = '571d8a2570a6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('assay_uploads', sa.Column('status_details', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('assay_uploads', 'status_details')
    # ### end Alembic commands ###
