"""Add user contact email column

Revision ID: aa2a1eff90cf
Revises: f7e888b7be33
Create Date: 2020-12-10 15:29:13.532275

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "aa2a1eff90cf"
down_revision = "f7e888b7be33"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("users", sa.Column("contact_email", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "contact_email")
    # ### end Alembic commands ###
