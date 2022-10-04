"""Add PACT user role

Revision ID: 6d997f27f5bf
Revises: 4aaabde150d3
Create Date: 2022-10-03 15:20:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "6d997f27f5bf"
down_revision = "4aaabde150d3"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Recreate the roles enum with 'pact-user' added as a value
    conn.execute("ALTER TABLE users ALTER role TYPE TEXT")
    conn.execute("DROP TYPE roles")
    conn.execute(
        """CREATE TYPE roles AS ENUM(
            'cidc-admin',
            'cidc-biofx-user',
            'cimac-biofx-user',
            'cimac-user',
            'developer',
            'devops',
            'nci-biobank-user',
            'network-viewer',
            'pact-user'
        )"""
    )
    conn.execute("ALTER TABLE users ALTER role TYPE roles USING role::roles")


def downgrade():
    conn = op.get_bind()

    # Clear roles for users who are 'pact-user's
    conn.execute("UPDATE users SET role = null WHERE role = 'pact-user'")

    # Recreate the roles enum without 'pact-user' as a value
    conn.execute("ALTER TABLE users ALTER role TYPE TEXT")
    conn.execute("DROP TYPE roles")
    conn.execute(
        """CREATE TYPE roles AS ENUM(
            'cidc-admin',
            'cidc-biofx-user',
            'cimac-biofx-user',
            'cimac-user',
            'developer',
            'devops',
            'nci-biobank-user',
            'network-viewer'
        )"""
    )
    conn.execute("ALTER TABLE users ALTER role TYPE roles USING role::roles")
