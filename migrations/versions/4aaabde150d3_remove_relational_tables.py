"""remove relational tables

Revision ID: 4aaabde150d3
Revises: 660c62cea77d
Create Date: 2022-09-14 20:52:13.298845

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4aaabde150d3'
down_revision = '660c62cea77d'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('ngs_assay_file_collections')  # before files and ngs_uploads
    op.drop_table('hande_records')  # before uploads and hande_images
    op.drop_table('hande_images')  # before files
    op.drop_table('files')
    op.drop_table('wes_records')  # before wes_uploads
    op.drop_table('wes_uploads')  # before ngs_uploads
    op.drop_table('ngs_uploads')  # after wes_uploads and ngs_assay_file_collections
    op.drop_index('upload_gcs_file_map_idx', table_name='uploads')  # before uploads
    op.drop_table('uploads')
    op.drop_table('aliquots')
    op.drop_table('samples')
    op.drop_table('collection_events')
    op.drop_table('shipments')
    op.drop_table('participants')
    op.drop_table('cohorts')
    op.drop_table('manifest_uploads')
    op.drop_table('clinical_trials')
    op.drop_table('assay_uploads')


def downgrade():    
    op.create_table(
        "assay_uploads",
        sa.Column("_created", sa.DateTime(), nullable=True),
        sa.Column("_updated", sa.DateTime(), nullable=True),
        sa.Column("_etag", sa.String(length=40), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table('clinical_trials',
    sa.Column('protocol_identifier', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('nct_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('nci_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('trial_name', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('trial_description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('trial_organization', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('grant_or_affiliated_network', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('trial_status', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('biobank', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('lead_cimac_pis', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('lead_cimac_contacts', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('lead_trial_staff', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('justification', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('biomarker_plan', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('data_sharing_plan', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('protocol_identifier', name='clinical_trials_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table(
        "manifest_uploads",
        sa.Column("_created", sa.DateTime(), nullable=True),
        sa.Column("_updated", sa.DateTime(), nullable=True),
        sa.Column("_etag", sa.String(length=40), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table('cohorts',
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('cohort_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['trial_id'], ['clinical_trials.protocol_identifier'], name='cohorts_trial_id_fkey'),
    sa.PrimaryKeyConstraint('trial_id', 'cohort_name', name='cohorts_pkey')
    )
    op.create_table('participants',
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('cimac_participant_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('trial_participant_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('cohort_name', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('gender', postgresql.ENUM('Male', 'Female', 'Not Specified', 'Other', name='gender_enum'), autoincrement=False, nullable=True),
    sa.Column('race', postgresql.ENUM('American Indian/Alaska Native', 'Asian', 'Black/African American', 'Native Hawaiian/Pacific Islander', 'White', 'Not Reported', 'Unknown', 'Other', name='race_enum'), autoincrement=False, nullable=True),
    sa.Column('ethnicity', postgresql.ENUM('Hispanic or Latino', 'Not Hispanic or Latino', 'Not reported', 'Unknown', 'Other', name='ethnicity_enum'), autoincrement=False, nullable=True),
    sa.Column('json_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['trial_id', 'cohort_name'], ['cohorts.trial_id', 'cohorts.cohort_name'], name='participants_trial_id_cohort_name_fkey'),
    sa.ForeignKeyConstraint(['trial_id'], ['clinical_trials.protocol_identifier'], name='participants_trial_id_fkey'),
    sa.PrimaryKeyConstraint('trial_id', 'cimac_participant_id', name='unique_trial_participant')
    )
    op.create_table('shipments',
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('manifest_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('assay_priority', postgresql.ENUM('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', 'Not Reported', 'Other', name='assay_priority_enum'), autoincrement=False, nullable=True),
    sa.Column('assay_type', postgresql.ENUM('ATACseq', 'CyTOF', 'ELISA', 'H&E', 'IHC', 'mIF', 'mIHC', 'Olink', 'RNAseq', 'TCRseq', 'WES', name='assay_enum'), autoincrement=False, nullable=True),
    sa.Column('courier', postgresql.ENUM('FEDEX', 'USPS', 'UPS', 'Inter-Site Delivery', name='courier_enum'), autoincrement=False, nullable=True),
    sa.Column('tracking_number', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('account_number', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('shipping_condition', postgresql.ENUM('Frozen_Dry_Ice', 'Frozen_Shipper', 'Ice_Pack', 'Ambient', 'Not Reported', 'Other', name='shipping_condition_enum'), autoincrement=False, nullable=True),
    sa.Column('date_shipped', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('date_received', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('quality_of_shipment', postgresql.ENUM('Specimen shipment received in good condition', 'Specimen shipment received in poor condition', 'Not Reported', 'Other', name='quality_of_shipment_enum'), autoincrement=False, nullable=True),
    sa.Column('ship_from', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('ship_to', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('receiving_party', postgresql.ENUM('MDA_Wistuba', 'MDA_Bernatchez', 'MDA_Al-Atrash', 'MSSM_Gnjatic', 'MSSM_Rahman', 'MSSM_Kim-Schulze', 'MSSM_Bongers', 'DFCI_Wu', 'DFCI_Hodi', 'DFCI_Severgnini', 'DFCI_Livak', 'Broad_Cibulskis', 'Stanf_Maecker', 'Stanf_Bendall', 'NCH', 'Adaptive', 'FNLCR_MoCha', name='receiving_party_enum'), autoincrement=False, nullable=True),
    sa.Column('json_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['trial_id'], ['clinical_trials.protocol_identifier'], name='shipments_trial_id_fkey'),
    sa.PrimaryKeyConstraint('trial_id', 'manifest_id', name='shipments_pkey'),
    sa.UniqueConstraint('manifest_id', name='shipments_manifest_id_key'),
    sa.UniqueConstraint('trial_id', 'manifest_id', name='unique_trial_manifest'),
    postgresql_ignore_search_path=False
    )
    op.create_table('collection_events',
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('event_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['trial_id'], ['clinical_trials.protocol_identifier'], name='collection_events_trial_id_fkey'),
    sa.PrimaryKeyConstraint('trial_id', 'event_name', name='collection_events_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('samples',
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('cimac_participant_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('collection_event_name', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('cimac_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('shipping_entry_number', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('box_number', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('surgical_pathology_report_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('clinical_report_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('parent_sample_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('processed_sample_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('site_description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('topography_code', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('topography_description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('histology_behavior', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('histology_behavior_description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('sample_location', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('type_of_sample', postgresql.ENUM('Tumor Tissue', 'Normal Tissue', 'Skin Tissue', 'Blood', 'Bone Marrow', 'Cerebrospinal Fluid', 'Lymph Node', 'Stool', 'Cell Product', 'White Blood Cell Apheresis', 'Not Reported', 'Other', name='sample_types_enum'), autoincrement=False, nullable=True),
    sa.Column('type_of_tumor_sample', postgresql.ENUM('Metastatic Tumor', 'Primary Tumor', 'Not Reported', 'Other', name='type_of_tumor_sample_enum'), autoincrement=False, nullable=True),
    sa.Column('sample_collection_procedure', postgresql.ENUM('Blood Draw', 'Excision', 'Core Biopsy', 'Punch Biopsy', 'Endoscopic Biopsy', 'Bone Marrow Core Biopsy', 'Bone Marrow Aspirate', 'Lumbar Puncture', 'Aspirate', 'Fine-Needle Aspiration', 'Not Reported', 'Other', name='sample_collection_procedure_enum'), autoincrement=False, nullable=True),
    sa.Column('core_number', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('fixation_stabilization_type', postgresql.ENUM('Archival FFPE', 'Fresh Specimen', 'Frozen Specimen', 'Formalin-Fixed Paraffin-Embedded', 'Optimum cutting temperature medium', 'Thaw-Lyse', 'Not Reported', 'Other', name='fixation_stabilization_type_enum'), autoincrement=False, nullable=True),
    sa.Column('type_of_primary_container', postgresql.ENUM('Sodium heparin', 'Blood specimen container with EDTA', 'Potassium EDTA', 'Streck Blood Collection Tube', 'Stool collection container with DNA stabilizer', 'Not Reported', 'Other', name='type_of_primary_container_enum'), autoincrement=False, nullable=True),
    sa.Column('sample_volume', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('sample_volume_units', postgresql.ENUM('Microliters', 'Milliliters', 'Not Reported', 'Other', name='volume_units_enum'), autoincrement=False, nullable=True),
    sa.Column('processed_sample_type', postgresql.ENUM('Whole Blood', 'Plasma', 'PBMC', 'Buffy Coat', 'Bone Marrow Mononuclear Cell', 'Supernatant', 'Cell Pellet', 'H&E-Stained Fixed Tissue Slide Specimen', 'Fixed Slide', 'Tissue Scroll', 'FFPE Punch', 'Not Reported', 'Other', name='processed_sample_type_enum'), autoincrement=False, nullable=True),
    sa.Column('processed_sample_volume', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('processed_sample_volume_units', postgresql.ENUM('Microliters', 'Milliliters', 'Not Reported', 'Other', name='volume_units_enum'), autoincrement=False, nullable=True),
    sa.Column('processed_sample_concentration', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('processed_sample_concentration_units', postgresql.ENUM('Nanogram per Microliter', 'Milligram per Milliliter', 'Micrograms per Microliter', 'Cells per Vial', 'Not Reported', 'Other', name='concentration_units_enum'), autoincrement=False, nullable=True),
    sa.Column('processed_sample_quantity', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('processed_sample_derivative', postgresql.ENUM('Tumor DNA', 'Tumor RNA', 'Germline DNA', 'Circulating Tumor-Derived DNA', 'Not Reported', 'Other', name='processed_sample_derivative_enum'), autoincrement=False, nullable=True),
    sa.Column('sample_derivative_volume', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('sample_derivative_volume_units', postgresql.ENUM('Microliters', 'Milliliters', 'Not Reported', 'Other', name='volume_units_enum'), autoincrement=False, nullable=True),
    sa.Column('sample_derivative_concentration', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('sample_derivative_concentration_units', postgresql.ENUM('Nanogram per Microliter', 'Milligram per Milliliter', 'Micrograms per Microliter', 'Cells per Vial', 'Not Reported', 'Other', name='concentration_units_enum'), autoincrement=False, nullable=True),
    sa.Column('tumor_tissue_total_area_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('viable_tumor_area_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('viable_stroma_area_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('necrosis_area_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('fibrosis_area_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('din', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('a260_a280', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('a260_a230', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('pbmc_viability', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('pbmc_recovery', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('pbmc_resting_period_used', postgresql.ENUM('Yes', 'No', 'Not Reported', 'Other', name='pbmc_resting_period_used_enum'), autoincrement=False, nullable=True),
    sa.Column('material_used', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('material_used_units', postgresql.ENUM('Microliters', 'Milliliters', 'Nanogram per Microliter', 'Milligram per Milliliter', 'Micrograms per Microliter', 'Cells per Vial', 'Slides', 'Not Reported', 'Other', name='material_units_enum'), autoincrement=False, nullable=True),
    sa.Column('material_remaining', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('material_remaining_units', postgresql.ENUM('Microliters', 'Milliliters', 'Nanogram per Microliter', 'Milligram per Milliliter', 'Micrograms per Microliter', 'Cells per Vial', 'Slides', 'Not Reported', 'Other', name='material_units_enum'), autoincrement=False, nullable=True),
    sa.Column('material_storage_condition', postgresql.ENUM('RT', '4oC', '(-20)oC', '(-80)oC', 'LN', 'Not Reported', 'Other', name='material_storage_condition_enum'), autoincrement=False, nullable=True),
    sa.Column('quality_of_sample', postgresql.ENUM('Pass', 'Fail', 'Not Reported', 'Other', name='quality_of_sample_enum'), autoincrement=False, nullable=True),
    sa.Column('sample_replacement', postgresql.ENUM('Replacement Not Requested', 'Replacement Requested', 'Replacement Tested', 'Not Reported', 'Other', name='replace_enum'), autoincrement=False, nullable=True),
    sa.Column('residual_sample_use', postgresql.ENUM('Sample Returned', 'Sample Sent to Another Lab', 'Sample received from CIMAC', 'Not Reported', 'Other', name='residual_sample_use_enum'), autoincrement=False, nullable=True),
    sa.Column('comments', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('diagnosis_verification', postgresql.ENUM('Local review not consistent with diagnostic pathology report', 'Local review consistent with diagnostic pathology report', 'Not Available', 'Not Reported', 'Other', name='diagnosis_verification_enum'), autoincrement=False, nullable=True),
    sa.Column('intended_assay', postgresql.ENUM('ATACseq', 'CyTOF', 'ELISA', 'H&E', 'IHC', 'mIF', 'mIHC', 'Olink', 'RNAseq', 'TCRseq', 'WES', name='assay_enum'), autoincrement=False, nullable=True),
    sa.Column('json_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('manifest_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['trial_id', 'cimac_participant_id'], ['participants.trial_id', 'participants.cimac_participant_id'], name='samples_trial_id_cimac_participant_id_fkey'),
    sa.ForeignKeyConstraint(['trial_id', 'collection_event_name'], ['collection_events.trial_id', 'collection_events.event_name'], name='samples_trial_id_collection_event_name_fkey'),
    sa.ForeignKeyConstraint(['trial_id', 'manifest_id'], ['shipments.trial_id', 'shipments.manifest_id'], name='samples_trial_id_manifest_id_fkey'),
    sa.PrimaryKeyConstraint('trial_id', 'cimac_id', name='unique_trial_sample'),
    sa.UniqueConstraint('cimac_id', name='unique_cimac_id'),
    postgresql_ignore_search_path=False
    )
    op.create_table('aliquots',
    sa.Column('sample_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('slide_number', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('quantity', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('aliquot_replacement', postgresql.ENUM('Replacement Not Requested', 'Replacement Requested', 'Replacement Tested', 'Not Reported', 'Other', name='replace_enum'), autoincrement=False, nullable=True),
    sa.Column('aliquot_status', postgresql.ENUM('Aliquot Returned', 'Aliquot Exhausted', 'Remainder used for other Assay', 'Aliquot Leftover', 'Other', name='aliquot_status_enum'), autoincrement=False, nullable=True),
    sa.Column('material_extracted', postgresql.ENUM('DNA', 'RNA', 'cfDNA', 'Other', name='material_extracted_enum'), autoincrement=False, nullable=True),
    sa.Column('extracted_concentration', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('aliquot_amount', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('lymphocyte_influx', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['sample_id'], ['samples.cimac_id'], name='aliquots_sample_id_fkey'),
    sa.PrimaryKeyConstraint('sample_id', 'slide_number', name='aliquots_pkey')
    )
    op.create_table('uploads',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('uploads_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('status', postgresql.ENUM('started', 'upload-completed', 'upload-failed', 'merge-completed', 'merge-failed', name='upload_status_enum'), server_default=sa.text("'started'::upload_status_enum"), autoincrement=False, nullable=False),
    sa.Column('token', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), autoincrement=False, nullable=False),
    sa.Column('status_details', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('multifile', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('gcs_file_map', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('gcs_xlsx_uri', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('upload_type', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('assay_creator', postgresql.ENUM('DFCI', 'Mount Sinai', 'Stanford', 'MD Anderson', 'TWIST', name='assay_creator_enum'), autoincrement=False, nullable=False),
    sa.Column('uploader_email', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('shipment_manifest_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['trial_id', 'shipment_manifest_id'], ['shipments.trial_id', 'shipments.manifest_id'], name='uploads_trial_id_shipment_manifest_id_fkey'),
    sa.ForeignKeyConstraint(['trial_id'], ['clinical_trials.protocol_identifier'], name='uploads_trial_id_fkey'),
    sa.ForeignKeyConstraint(['uploader_email'], ['users.email'], name='uploads_uploader_email_fkey'),
    sa.PrimaryKeyConstraint('id', 'trial_id', name='uploads_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('ngs_uploads',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('sequencer_platform', postgresql.ENUM('Illumina - HiSeq 2500', 'Illumina - HiSeq 3000', 'Illumina - NextSeq 550', 'Illumina - HiSeq 4000', 'Illumina - NovaSeq 6000', 'MiSeq', name='sequencer_platform_enum'), autoincrement=False, nullable=True),
    sa.Column('library_kit', postgresql.ENUM('Hyper Prep ICE Exome Express: 1.0', 'KAPA HyperPrep', 'IDT duplex UMI adapters', 'TWIST', name='library_kit_enum'), autoincrement=False, nullable=True),
    sa.Column('paired_end_reads', postgresql.ENUM('Paired', 'Single', name='paired_end_reads_enum'), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['id', 'trial_id'], ['uploads.id', 'uploads.trial_id'], name='ngs_uploads_id_trial_id_fkey'),
    sa.PrimaryKeyConstraint('id', 'trial_id', name='ngs_uploads_pkey')
    )
    op.create_index('upload_gcs_file_map_idx', 'uploads', ['gcs_file_map'], unique=False)
    op.create_table('wes_uploads',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('sequencing_protocol', postgresql.ENUM('Express Somatic Human WES (Deep Coverage) v1.1', 'Somatic Human WES v6', 'TWIST', name='sequencing_protocol_enum'), autoincrement=False, nullable=True),
    sa.Column('bait_set', postgresql.ENUM('whole_exome_illumina_coding_v1', 'broad_custom_exome_v1', 'TWIST Dana Farber Custom Panel', 'TWIST Custom Panel PN 101042', name='bait_set_enum'), autoincrement=False, nullable=False),
    sa.Column('read_length', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['id', 'trial_id'], ['ngs_uploads.id', 'ngs_uploads.trial_id'], name='wes_uploads_id_trial_id_fkey'),
    sa.PrimaryKeyConstraint('id', 'trial_id', name='wes_uploads_pkey')
    )
    op.create_table('wes_records',
    sa.Column('upload_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('cimac_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('sequencing_date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('quality_flag', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['trial_id', 'cimac_id'], ['samples.trial_id', 'samples.cimac_id'], name='wes_records_trial_id_cimac_id_fkey'),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id'], ['uploads.trial_id', 'uploads.id'], name='wes_records_trial_id_upload_id_fkey'),
    sa.PrimaryKeyConstraint('upload_id', 'cimac_id', name='wes_records_pkey')
    )
    op.create_table('files',
    sa.Column('object_url', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('upload_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('local_path', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('upload_placeholder', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('artifact_creator', postgresql.ENUM('DFCI', 'Mount Sinai', 'Stanford', 'MD Anderson', name='artifact_creator_enum'), autoincrement=False, nullable=True),
    sa.Column('uploader', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('file_name', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('uploaded_timestamp', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('md5_hash', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('crc32_hash', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('artifact_category', postgresql.ENUM('Assay Artifact from CIMAC', 'Pipeline Artifact', 'Manifest File', name='artifact_category_enum'), autoincrement=False, nullable=True),
    sa.Column('data_format', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('facet_group', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id'], ['uploads.trial_id', 'uploads.id'], name='files_trial_id_upload_id_fkey'),
    sa.PrimaryKeyConstraint('object_url', 'upload_id', name='files_pkey'),
    sa.UniqueConstraint('local_path', name='files_local_path_key'),
    sa.UniqueConstraint('trial_id', 'upload_id', 'object_url', name='files_trial_id_upload_id_object_url_key')
    )
    op.create_table('hande_images',
    sa.Column('object_url', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('upload_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['upload_id', 'object_url'], ['files.upload_id', 'files.object_url'], name='hande_images_upload_id_object_url_fkey'),
    sa.PrimaryKeyConstraint('object_url', name='hande_images_pkey')
    )
    op.create_table('hande_records',
    sa.Column('cimac_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('image_url', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('tumor_tissue_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('viable_tumor_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('viable_stroma_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('necrosis_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('fibrosis_percentage', sa.NUMERIC(), autoincrement=False, nullable=True),
    sa.Column('comment', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('upload_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['trial_id', 'cimac_id'], ['samples.trial_id', 'samples.cimac_id'], name='hande_records_trial_id_cimac_id_fkey'),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id'], ['uploads.trial_id', 'uploads.id'], name='hande_records_trial_id_upload_id_fkey')
    )
    op.create_table('ngs_assay_file_collections',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('upload_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('cimac_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('trial_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('r1_object_url', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('r2_object_url', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('lane', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('bam_object_url', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('number', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.CheckConstraint('((r1_object_url IS NOT NULL) AND (r2_object_url IS NOT NULL)) OR (bam_object_url IS NOT NULL)', name='ngs_assay_file_collections_check'),
    sa.ForeignKeyConstraint(['trial_id', 'cimac_id'], ['samples.trial_id', 'samples.cimac_id'], name='ngs_assay_file_collections_trial_id_cimac_id_fkey'),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id', 'bam_object_url'], ['files.trial_id', 'files.upload_id', 'files.object_url'], name='ngs_assay_file_collections_trial_id_upload_id_bam_object_u_fkey'),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id', 'r1_object_url'], ['files.trial_id', 'files.upload_id', 'files.object_url'], name='ngs_assay_file_collections_trial_id_upload_id_r1_object_ur_fkey'),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id', 'r2_object_url'], ['files.trial_id', 'files.upload_id', 'files.object_url'], name='ngs_assay_file_collections_trial_id_upload_id_r2_object_ur_fkey'),
    sa.ForeignKeyConstraint(['trial_id', 'upload_id'], ['ngs_uploads.trial_id', 'ngs_uploads.id'], name='ngs_assay_file_collections_trial_id_upload_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='ngs_assay_file_collections_pkey')
    )
