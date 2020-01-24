"""empty message

Revision ID: cadb45e45e2b
Revises: 1b74e4d0bb7f
Create Date: 2020-01-24 13:17:57.842983

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "cadb45e45e2b"
down_revision = "1b74e4d0bb7f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "upload_jobs",
        sa.Column("_created", sa.DateTime(), nullable=True),
        sa.Column("_updated", sa.DateTime(), nullable=True),
        sa.Column("_etag", sa.String(length=40), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "started",
                "upload-completed",
                "upload-failed",
                "merge-completed",
                "merge-failed",
                name="assay_upload_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("status_details", sa.String(), nullable=True),
        sa.Column("multifile", sa.Boolean(), nullable=False),
        sa.Column(
            "gcs_file_map", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("gcs_xlsx_uri", sa.String(), nullable=False),
        sa.Column(
            "metadata_patch", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("upload_type", sa.String(), nullable=False),
        sa.Column("uploader_email", sa.String(), nullable=True),
        sa.Column("trial_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["trial_id"], ["trial_metadata.trial_id"]),
        sa.ForeignKeyConstraint(
            ["uploader_email"], ["users.email"], onupdate="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_upload_jobs_trial_id"), "upload_jobs", ["trial_id"], unique=False
    )
    op.create_index(
        "upload_jobs_gcs_gcs_file_map_idx",
        "upload_jobs",
        ["gcs_file_map"],
        unique=False,
        postgresql_using="gin",
    )

    conn = op.get_bind()

    # Transfer data from assay_uploads to upload_jobs
    conn.execute(
        """
        INSERT INTO upload_jobs(multifile, _created, _updated, _etag, status, status_details, gcs_file_map, gcs_xlsx_uri, metadata_patch, upload_type, uploader_email, trial_id)
        SELECT true, _created, _updated, _etag, status, status_details, gcs_file_map, gcs_xlsx_uri, assay_patch, assay_type, uploader_email, trial_id from assay_uploads
        """
    )

    # Transfer data from manifest_uploads to upload_jobs
    conn.execute(
        """
        INSERT INTO upload_jobs(multifile, _created, _updated, _etag, status, status_details, gcs_file_map, gcs_xlsx_uri, metadata_patch, upload_type, uploader_email, trial_id)
        SELECT false, _created, _updated, _etag, 'merge-completed', null, null, gcs_xlsx_uri, metadata_patch, manifest_type, uploader_email, trial_id from manifest_uploads
        """
    )

    op.drop_index("ix_manifest_uploads_trial_id", table_name="manifest_uploads")
    op.drop_table("manifest_uploads")
    op.drop_index("assay_uploads_gcs_gcs_file_map_idx", table_name="assay_uploads")
    op.drop_index("ix_assay_uploads_trial_id", table_name="assay_uploads")
    op.drop_table("assay_uploads")

    conn.execute("ALTER TYPE assay_upload_status RENAME TO upload_job_status")


def downgrade():
    op.create_table(
        "assay_uploads",
        sa.Column(
            "_created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "_updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("_etag", sa.VARCHAR(length=40), autoincrement=False, nullable=True),
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "started",
                "upload-completed",
                "upload-failed",
                "merge-completed",
                "merge-failed",
                name="upload_job_status",
                create_type=False,
            ),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "assay_patch",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("uploader_email", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("assay_type", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("trial_id", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("gcs_xlsx_uri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "gcs_file_map",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("status_details", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["trial_id"],
            ["trial_metadata.trial_id"],
            name="assay_uploads_trial_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["uploader_email"],
            ["users.email"],
            name="upload_jobs_uploader_email_fkey",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="assay_uploads_pkey"),
    )
    op.create_index(
        "ix_assay_uploads_trial_id", "assay_uploads", ["trial_id"], unique=False
    )
    op.create_index(
        "assay_uploads_gcs_gcs_file_map_idx",
        "assay_uploads",
        ["gcs_file_map"],
        unique=False,
    )
    op.create_table(
        "manifest_uploads",
        sa.Column(
            "_created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "_updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("_etag", sa.VARCHAR(length=40), autoincrement=False, nullable=True),
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("gcs_xlsx_uri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("uploader_email", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("trial_id", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("manifest_type", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "metadata_patch",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["trial_id"],
            ["trial_metadata.trial_id"],
            name="manifest_uploads_trial_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["uploader_email"],
            ["users.email"],
            name="manifest_uploads_uploader_email_fkey",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="manifest_uploads_pkey"),
    )
    op.create_index(
        "ix_manifest_uploads_trial_id", "manifest_uploads", ["trial_id"], unique=False
    )

    conn = op.get_bind()

    # Transfer data from upload_jobs to assay_uploads
    conn.execute(
        """
        INSERT INTO assay_uploads( _created, _updated, _etag, status, status_details, gcs_file_map, gcs_xlsx_uri, assay_patch, assay_type, uploader_email, trial_id)
        SELECT _created, _updated, _etag, status, status_details, gcs_file_map, gcs_xlsx_uri, metadata_patch, upload_type, uploader_email, trial_id from upload_jobs
        """
    )

    # Transfer data from upload_jobs to manifest_uploads
    conn.execute(
        """
        INSERT INTO manifest_uploads(_created, _updated, _etag, gcs_xlsx_uri, metadata_patch, manifest_type, uploader_email, trial_id)
        SELECT _created, _updated, _etag, gcs_xlsx_uri, metadata_patch, upload_type, uploader_email, trial_id from upload_jobs
        """
    )

    conn.execute("ALTER TYPE upload_job_status RENAME TO assay_upload_status")

    op.drop_index("upload_jobs_gcs_gcs_file_map_idx", table_name="upload_jobs")
    op.drop_index(op.f("ix_upload_jobs_trial_id"), table_name="upload_jobs")
    op.drop_table("upload_jobs")
