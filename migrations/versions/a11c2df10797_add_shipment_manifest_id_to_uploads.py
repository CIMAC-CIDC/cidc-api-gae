"""add shipment_manifest_id to uploads

Revision ID: a11c2df10797
Revises: cf67f9b91d10
Create Date: 2021-09-29 16:18:53.702733

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a11c2df10797'
down_revision = 'cf67f9b91d10'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('uploads', sa.Column('shipment_manifest_id', sa.String(), nullable=True))
    op.create_foreign_key(None, 'uploads', 'shipments', ['trial_id', 'shipment_manifest_id'], ['trial_id', 'manifest_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'uploads', type_='foreignkey')
    op.drop_column('uploads', 'shipment_manifest_id')
    # ### end Alembic commands ###
