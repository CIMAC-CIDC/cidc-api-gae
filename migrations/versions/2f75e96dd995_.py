"""empty message

Revision ID: 2f75e96dd995
Revises: 4bc7f3b6b092
Create Date: 2019-08-28 17:33:02.279980

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2f75e96dd995"
down_revision = "4bc7f3b6b092"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE IF EXISTS upload_jobs RENAME TO assay_uploads")
    op.execute(
        "ALTER TABLE IF EXISTS assay_uploads RENAME COLUMN metadata_json_patch TO assay_patch"
    )
    op.execute(
        "ALTER SEQUENCE IF EXISTS upload_jobs_id_seq RENAME TO assay_uploads_id_seq"
    )
    op.execute("ALTER INDEX IF EXISTS upload_jobs_pkey RENAME TO assay_uploads_pkey")
    op.execute(
        "ALTER INDEX IF EXISTS gcs_objects_idx RENAME TO assay_uploads_gcs_file_uris_idx"
    )
    op.add_column("assay_uploads", sa.Column("trial_id", sa.String(), nullable=True))
    op.execute(
        "UPDATE assay_uploads SET trial_id = assay_patch->>'lead_organisation_study_id'"
    )
    op.alter_column(
        "assay_uploads", "trial_id", existing_type=sa.VARCHAR(), nullable=False
    )
    op.create_foreign_key(
        "assay_uploads_trial_id_fkey",
        "assay_uploads",
        "trial_metadata",
        ["trial_id"],
        ["trial_id"],
    )
    op.create_index(
        op.f("ix_assay_uploads_trial_id"), "assay_uploads", ["trial_id"], unique=False
    )

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "manifest_uploads",
        sa.Column("_created", sa.DateTime(), nullable=True),
        sa.Column("_updated", sa.DateTime(), nullable=True),
        sa.Column("_etag", sa.String(length=40), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "manifest_patch", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("gcs_xlsx_uri", sa.String(), nullable=False),
        sa.Column("uploader_email", sa.String(), nullable=True),
        sa.Column("trial_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["trial_id"], ["trial_metadata.trial_id"]),
        sa.ForeignKeyConstraint(
            ["uploader_email"], ["users.email"], onupdate="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_manifest_uploads_trial_id"),
        "manifest_uploads",
        ["trial_id"],
        unique=False,
    )


def downgrade():
    op.execute("ALTER TABLE IF EXISTS assay_uploads RENAME TO upload_jobs")
    op.execute(
        "ALTER TABLE IF EXISTS upload_jobs RENAME COLUMN assay_patch TO metadata_json_patch"
    )
    op.execute("ALTER SEQUENCE assay_uploads_id_seq RENAME TO upload_jobs_id_seq")
    op.execute("ALTER INDEX assay_uploads_pkey RENAME TO upload_jobs_pkey")
    op.execute(
        "ALTER INDEX IF EXISTS assay_uploads_gcs_file_uris_idx RENAME TO gcs_objects_idx"
    )
    op.delete_foreign_key("assay_uploads_trial_id_fkey")
    op.drop_index(op.f("ix_assay_uploads_trial_id"), table_name="assay_uploads")

    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_manifest_uploads_trial_id"), table_name="manifest_uploads")
    op.drop_table("manifest_uploads")
    # ### end Alembic commands ###
