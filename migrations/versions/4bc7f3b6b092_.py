"""empty message

Revision ID: 4bc7f3b6b092
Revises: 6378d4ed779f
Create Date: 2019-08-28 16:42:41.642969

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4bc7f3b6b092"
down_revision = "6378d4ed779f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "downloadable_files", sa.Column("assay_type", sa.String(), nullable=True)
    )
    op.execute("UPDATE downloadable_files SET assay_type = 'wes'")
    op.alter_column(
        "downloadable_files", "assay_type", existing_type=sa.VARCHAR(), nullable=False
    )
    op.drop_column("downloadable_files", "assay_category")
    op.drop_column("downloadable_files", "file_type")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "downloadable_files",
        sa.Column(
            "file_type",
            postgresql.ENUM(
                "FASTA",
                "FASTQ",
                "TIFF",
                "VCF",
                "TSV",
                "Excel",
                "NPX",
                "BAM",
                "MAF",
                "PNG",
                "JPG",
                "XML",
                "Other",
                name="file_type",
            ),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "downloadable_files",
        sa.Column(
            "assay_category",
            postgresql.ENUM(
                "Whole Exome Sequencing (WES)",
                "RNASeq",
                "Conventional Immunohistochemistry",
                "Multiplex Immunohistochemistry",
                "Multiplex Immunofluorescence",
                "CyTOF",
                "OLink",
                "NanoString",
                "ELISpot",
                "Multiplexed Ion-Beam Imaging (MIBI)",
                "Other",
                "None",
                name="assay_category",
            ),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_column("downloadable_files", "assay_type")
    # ### end Alembic commands ###
