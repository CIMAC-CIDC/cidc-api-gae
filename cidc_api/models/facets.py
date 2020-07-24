from typing import Dict, List, Optional

from sqlalchemy.sql import ClauseElement

from .models import DownloadableFiles

like = DownloadableFiles.object_url.like

# Represent available downloadable file assay facets as a dictionary
# mapping an assay names to assay subfacet dictionaries. An assay subfacet
# dictionary maps subfacet names to a list of SQLAlchemy filter clause elements
# for looking up files associated with the given subfacet.
assay_facets: Dict[str, Dict[str, List[ClauseElement]]] = {
    "cytof": {
        "source": [
            like("%source_%.fcs"),
            like("%spike_in_fcs.fcs"),
            like("%normalized_and_debarcoded.fcs"),
            like("%processed.fcs"),
        ],
        "cell counts": [
            like("%cell_counts_assignment.csv"),
            like("%cell_counts_compartment.csv"),
            like("%cell_counts_profiling.csv"),
        ],
        "labeled source": [like("%source.fcs")],
        "analysis results": [like("%analysis.zip"), like("%results.zip")],
        "key": [
            like("%assignment.csv"),
            like("%compartment.csv"),
            like("%profiling.csv"),
        ],
    },
    "wes": {
        "source": [
            like("%wes%reads_%.bam"),
            like("%wes%r1_%.fastq.gz"),
            like("%wes%r2_%.fastq.gz"),
        ],
        "germline": [like("%vcfcompare.txt"), like("%optimalpurityvalue.txt")],
        "clonality": [like("%clonality_pyclone.tsv")],
        "copy number": [
            like("%copynumber_cnvcalls.txt"),
            like("%copynumber_cnvcalls.txt.tn.tsv"),
        ],
        "neoantigen": [
            like("%MHC_Class_I_all_epitopes.tsv"),
            like("%MHC_Class_I_filtered_condensed_ranked.tsv"),
            like("%MHC_Class_II_all_epitopes.tsv"),
            like("%MHC_Class_II_filtered_condensed_ranked.tsv"),
        ],
        "somatic": [
            like("%vcf_tnscope_output.vcf"),
            like("%maf_tnscope_output.maf"),
            like("%vcf_tnscope_filter.vcf"),
            like("%maf_tnscope_filter.maf"),
            like("%tnscope_exons_broad.gz"),
            like("%tnscope_exons_mda.gz"),
            like("%tnscope_exons_mocha.gz"),
        ],
        "alignment": [
            like("%tn_corealigned.bam"),
            like("%tn_corealigned.bam.bai"),
            like("%recalibrated.bam"),
            like("%recalibrated.bam.bai"),
            like("%sorted.dedup.bam"),
            like("%sorted.dedup.bam.bai"),
        ],
        "metrics": [
            like("%all_sample_summaries.txt"),
            like("%coverage_metrics.txt"),
            like("%target_metrics.txt"),
            like("%coverage_metrics_summary.txt"),
            like("%target_metrics_summary.txt"),
            like("%mosdepth_region_dist_broad.txt"),
            like("%mosdepth_region_dist_mda.txt"),
            like("%mosdepth_region_dist_mocha.txt"),
            like("%optitype_result.tsv"),
        ],
        "hla type": [like("%optitype_result.tsv")],
        "report": [like("%wes_version.txt")],
    },
    "rna": {
        "source": [
            like("%rna%reads_%.bam"),
            like("%rna%r1_%.fastq.gz"),
            like("%rna%r2_%.fastq.gz"),
        ],
        "alignment": [
            like("%sorted.bam"),
            like("%sorted.bam.bai"),
            like("%sorted.bam.stat.txt"),
            like("%downsampling.bam"),
            like("%downsampling.bam.bai"),
        ],
        "quality": [
            like("%downsampling_housekeeping.bam"),
            like("%downsampling_housekeeping.bam.bai"),
            like("%read_distrib.txt"),
            like("%tin_score.txt"),
            like("%tin_score.summary.txt"),
        ],
        "gene quantification": [
            like("%quant.sf"),
            like("%transcriptome.bam.log"),
            like("%aux_info_ambig_info.tsv"),
            like("%aux_info_expected_bias.gz"),
            like("%aux_info_fld.gz"),
            like("%aux_info_meta_info.json"),
            like("%aux_info_observed_bias.gz"),
            like("%aux_info_observed_bias_3p.gz"),
            like("%cmd_info.json"),
            like("%salmon_quant.log"),
        ],
    },
}
