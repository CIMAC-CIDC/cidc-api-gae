"""check types and defaults

Revision ID: 4c7e810cedea
Revises: 6d997f27f5bf
Create Date: 2023-05-08 15:16:16.778041

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '4c7e810cedea'
down_revision = '6d997f27f5bf'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Recreate the orgs enum with 'N/A' added as a value
    conn.execute("ALTER TABLE users ALTER organization TYPE TEXT")
    conn.execute("DROP TYPE orgs")
    conn.execute(
        """CREATE TYPE orgs AS ENUM(
            'CIDC',
            'DFCI',
            'ICAHN',
            'STANFORD',
            'ANDERSON',
            'N/A'
        )"""
    )
    conn.execute("ALTER TABLE users ALTER organization TYPE orgs USING organization::orgs")


def downgrade():
    conn = op.get_bind()

    # Clear orgs for users who are 'N/A's
    conn.execute("UPDATE users SET organization = null WHERE organization = 'N/A'")

    # Recreate the orgs enum without 'N/A' as a value
    conn.execute("ALTER TABLE users ALTER organization TYPE TEXT")
    conn.execute("DROP TYPE orgs")
    conn.execute(
        """CREATE TYPE orgs AS ENUM(
            'CIDC',
            'DFCI',
            'ICAHN',
            'STANFORD',
            'ANDERSON'
        )"""
    )
    conn.execute("ALTER TABLE users ALTER organization TYPE orgs USING organization::orgs")
