"""empty message

Revision ID: cf67f9b91d10
Revises: a90dd4593e54
Create Date: 2021-07-29 18:46:18.428942

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cf67f9b91d10'
down_revision = 'a90dd4593e54'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(None, 'files', ['trial_id', 'upload_id', 'object_url'])
    op.create_unique_constraint(None, 'files', ['local_path'])

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ngs_uploads',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('trial_id', sa.String(), nullable=False),
    sa.Column('sequencer_platform', sa.Enum('Illumina - HiSeq 2500', 'Illumina - HiSeq 3000', 'Illumina - NextSeq 550', 'Illumina - HiSeq 4000', 'Illumina - NovaSeq 6000', 'MiSeq', name='sequencer_platform_enum'), nullable=True),
    sa.Column('library_kit', sa.Enum('Hyper Prep ICE Exome Express: 1.0', 'KAPA HyperPrep', 'IDT duplex UMI adapters', 'TWIST', name='library_kit_enum'), nullable=True),
    sa.Column('paired_end_reads', sa.Enum('Paired', 'Single', name='paired_end_reads_enum'), nullable=True),
    sa.ForeignKeyConstraint(['id', 'trial_id'], ['uploads.id', 'uploads.trial_id'], ),
    sa.PrimaryKeyConstraint('id', 'trial_id')
    )
    op.create_table('wes_uploads',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('trial_id', sa.String(), nullable=False),
    sa.Column('sequencing_protocol', sa.Enum('Express Somatic Human WES (Deep Coverage) v1.1', 'Somatic Human WES v6', 'TWIST', name='sequencing_protocol_enum'), nullable=True),
    sa.Column('bait_set', sa.Enum('whole_exome_illumina_coding_v1', 'broad_custom_exome_v1', 'TWIST Dana Farber Custom Panel', 'TWIST Custom Panel PN 101042', name='bait_set_enum'), nullable=False),
    sa.Column('read_length', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id', 'trial_id'], ['ngs_uploads.id', 'ngs_uploads.trial_id'], ),
    sa.PrimaryKeyConstraint('id', 'trial_id')
    )
    op.create_table('ngs_assay_file_collections',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('upload_id', sa.Integer(), nullable=False),
    sa.Column('cimac_id', sa.String(), nullable=False),
    sa.Column('trial_id', sa.String(), nullable=False),
    sa.Column('r1_object_url', sa.String(), nullable=True),
    sa.Column('r2_object_url', sa.String(), nullable=True),
    sa.Column('lane', sa.Integer(), nullable=True),
    sa.Column('bam_object_url', sa.String(), nullable=True),
    sa.Column('number', sa.Integer(), nullable=True),
    sa.CheckConstraint('(r1_object_url is not null and r2_object_url is not null) or bam_object_url is not null'),
    sa.ForeignKeyConstraint(['trial_id', 'cimac_id'], ['samples.trial_id', 'samples.cimac_id'], ),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id', 'bam_object_url'], ['files.trial_id', 'files.upload_id', 'files.object_url'], ),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id', 'r1_object_url'], ['files.trial_id', 'files.upload_id', 'files.object_url'], ),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id', 'r2_object_url'], ['files.trial_id', 'files.upload_id', 'files.object_url'], ),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id'], ['ngs_uploads.trial_id', 'ngs_uploads.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('wes_records',
    sa.Column('upload_id', sa.Integer(), nullable=False),
    sa.Column('cimac_id', sa.String(), nullable=False),
    sa.Column('trial_id', sa.String(), nullable=False),
    sa.Column('sequencing_date', sa.Date(), nullable=True),
    sa.Column('quality_flag', sa.Numeric(), nullable=True),
    sa.ForeignKeyConstraint(['trial_id', 'cimac_id'], ['samples.trial_id', 'samples.cimac_id'], ),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id'], ['uploads.trial_id', 'uploads.id'], ),
    sa.PrimaryKeyConstraint('upload_id', 'cimac_id')
    )
    op.add_column('hande_records', sa.Column('upload_id', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'hande_records', 'uploads', ['trial_id', 'upload_id'], ['trial_id', 'id'])
    op.drop_column('hande_records', 'assay_id')
    op.create_unique_constraint('unique_trial_manifest', 'shipments', ['trial_id', 'manifest_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('unique_trial_manifest', 'shipments', type_='unique')
    op.add_column('hande_records', sa.Column('assay_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'hande_records', type_='foreignkey')
    op.drop_column('hande_records', 'upload_id')
    op.drop_constraint(None, 'files', type_='unique')
    op.drop_table('wes_records')
    op.drop_table('ngs_assay_file_collections')
    op.drop_table('wes_uploads')
    op.drop_table('ngs_uploads')
    # ### end Alembic commands ###
