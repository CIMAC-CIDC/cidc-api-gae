from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Union

from werkzeug.exceptions import BadRequest


class FacetConfig:
    facet_groups: List[str]
    description: Optional[str]

    def __init__(self, facet_groups: List[str], description: Optional[str] = None):
        self.facet_groups = facet_groups
        self.description = description


Facets = Dict[str, Union[FacetConfig, Dict[str, FacetConfig]]]

# Represent available downloadable file assay facets as a dictionary
# mapping an assay names to assay subfacet dictionaries. An assay subfacet
# dictionary maps subfacet names to a list of SQLAlchemy filter clause elements
# for looking up files associated with the given subfacet.
assay_facets: Facets = {
    "Miscellaneous": {"All": FacetConfig(["/misc_data/"])},
    "Nanostring": {
        "Source": FacetConfig(
            ["/nanostring/.rcc", "/nanostring/control.rcc"],
            "direct output from a single NanoString run",
        ),
        "Data": FacetConfig(
            ["/nanostring/raw_data.csv", "/nanostring/normalized_data.csv"],
            "Tabulated data across all samples in a batch",
        ),
    },
    "ATAC-Seq": {
        "Source": FacetConfig(
            [
                "/atacseq/r1_L.fastq.gz",
                "/atacseq/r2_L.fastq.gz",
                "/atacseq/analysis/aligned_sorted.bam",
            ]
        ),
        "Peaks": FacetConfig(
            [
                "/atacseq/analysis/peaks/sorted_peaks.bed",
                "/atacseq/analysis/peaks/sorted_summits.bed",
                "/atacseq/analysis/peaks/sorted_peaks.narrowPeak",
                "/atacseq/analysis/peaks/treat_pileup.bw",
            ]
        ),
    },
    "CyTOF": {
        "Source": FacetConfig(
            [
                "/cytof/spike_in.fcs",
                "/cytof/source_.fcs",
                "/cytof/debarcoding_key.csv",
                "/cytof/processed.fcs",
                "/cytof/controls/processed.fcs",
                "/cytof/controls/spike_in.fcs",
            ],
            "De-barcoded, concatenated and de-multipled fcs files",
        ),
        "Cell Counts": FacetConfig(
            [
                "/cytof_analysis/cell_counts_assignment.csv",
                "/cytof_analysis/cell_counts_compartment.csv",
                "/cytof_analysis/cell_counts_profiling.csv",
            ],
            "Summary cell count expression of individual cell types in each sample",
        ),
        "Combined Cell Counts": FacetConfig(
            [
                "csv|cell counts assignment",
                "csv|cell counts compartment",
                "csv|cell counts profiling",
            ],
            "Summary cell counts, combined across all samples in the trial",
        ),
        "Labeled Source": FacetConfig(
            ["/cytof_analysis/source.fcs"],
            "FCS file with enumerations for compartment, assignment and profiling cell labels",
        ),
        "Analysis Results": FacetConfig(
            ["/cytof_analysis/reports.zip", "/cytof_analysis/analysis.zip"],
            "Results package from Astrolabe analysis",
        ),
        "Control Files Analysis": FacetConfig(
            ["/cytof_analysis/control_files_analysis.zip"],
        ),
        "Key": FacetConfig(
            [
                "/cytof_analysis/assignment.csv",
                "/cytof_analysis/compartment.csv",
                "/cytof_analysis/profiling.csv",
            ],
            "Keys for mapping from respective enumeration indices to the cell labels",
        ),
    },
    "WES": {
        "Source": FacetConfig(
            [
                "/wes/r1_L.fastq.gz",
                "/wes/r2_L.fastq.gz",
                "/wes/reads_.bam",
            ]
        ),
        "Germline": FacetConfig(
            [
                "/wes/analysis/tumor/haplotyper_targets.vcf.gz",
                "/wes/analysis/normal/haplotyper_targets.vcf.gz",
                "/wes/analysis/tumor/haplotyper_output.vcf",
                "/wes/analysis/normal/haplotyper_output.vcf",
            ]
        ),
        "Purity": FacetConfig(
            [
                "/wes/analysis/optimal_purity_value.txt",
                "/wes/analysis/alternative_solutions.txt",
                "/wes/analysis/cp_contours.pdf",
            ]
        ),
        "Clonality": FacetConfig(
            [
                "/wes/analysis/clonality_pyclone.tsv",
                "/wes/analysis/clonality_table.tsv",
                "/wes/analysis/clonality_input.tsv",
                "/wes/analysis/clonality_results.tsv",
                "/wes/analysis/clonality_summary.tsv",
            ]
        ),
        "Copy Number": FacetConfig(
            [
                "/wes/analysis/copynumber_cnvcalls.txt",
                "/wes/analysis/copynumber_cnvcalls.txt.tn.tsv",
                "/wes/analysis/copynumber_segments.txt",
                "/wes/analysis/copynumber_genome_view.pdf",
                "/wes/analysis/copynumber_chromosome_view.pdf",
                "/wes/analysis/copynumber_sequenza_gainloss.bed",
                "/wes/analysis/copynumber_sequenza_final.txt.gz",
                "/wes/analysis/copynumber_consensus.bed",
                "/wes/analysis/copynumber_consensus_gain.bed",
                "/wes/analysis/copynumber_consensus_loss.bed",
                "/wes/analysis/copynumber_facets.cncf",
                "/wes/analysis/copynumber_facets_gainloss.bed",
                "/wes/analysis/copynumber_cnv_segments.cns",
                "/wes/analysis/copynumber_cnv_segments_enhanced.cns",
                "/wes/analysis/copynumber_cnv_scatterplot.png",
                "/wes/analysis/copynumber_cnvkit_gainloss.bed",
            ]
        ),
        "Neoantigen": FacetConfig(["/wes/analysis/combined_filtered.tsv"]),
        "Somatic": FacetConfig(
            [
                "/wes/analysis/vcf_gz_tnscope_output.vcf.gz",
                "/wes/analysis/maf_tnscope_output.maf",
                "/wes/analysis/vcf_gz_tnscope_filter.vcf.gz",
                "/wes/analysis/maf_tnscope_filter.maf",
                "/wes/analysis/tnscope_exons.vcf.gz",
                "/wes/analysis/vcf_compare.txt",
                "/wes/analysis/tnscope_output_twist.vcf",
                "/wes/analysis/tnscope_output_twist.maf",
                "/wes/analysis/tnscope_output_twist_filtered.vcf",
                "/wes/analysis/tnscope_output_twist_filtered.maf",
            ]
        ),
        "TcellExtrect": FacetConfig(["/wes/analysis/tcellextrect.txt"]),
        "Alignment": FacetConfig(
            [
                "/wes/analysis/tumor/sorted.dedup.bam",
                "/wes/analysis/tumor/sorted.dedup.bam.bai",
                "/wes/analysis/normal/sorted.dedup.bam",
                "/wes/analysis/normal/sorted.dedup.bam.bai",
                "/wes/analysis/tumor/recalibrated.bam",
                "/wes/analysis/tumor/recalibrated.bam.bai",
                "/wes/analysis/normal/recalibrated.bam",
                "/wes/analysis/normal/recalibrated.bam.bai",
            ]
        ),
        "Metrics": FacetConfig(
            [
                "/wes/analysis/tumor/coverage_metrics.txt",
                "/wes/analysis/tumor/target_metrics.txt",
                "/wes/analysis/tumor/coverage_metrics_summary.txt",
                "/wes/analysis/normal/coverage_metrics.txt",
                "/wes/analysis/normal/target_metrics.txt",
                "/wes/analysis/normal/coverage_metrics_summary.txt",
            ]
        ),
        "HLA Type": FacetConfig(
            [
                "/wes/analysis/tumor/hla_final_result.txt",
                "/wes/analysis/normal/hla_final_result.txt",
                "/wes/analysis/tumor/optitype_result.tsv",
                "/wes/analysis/normal/optitype_result.tsv",
                "/wes/analysis/tumor/xhla_report_hla.json",
                "/wes/analysis/normal/xhla_report_hla.json",
                "/wes/analysis/HLA_results.tsv",
            ]
        ),
        "Report": FacetConfig(
            [
                "/wes/analysis/tumor_mutational_burden.tsv",
                "/wes/analysis/report.tar.gz",
                "/wes/analysis/wes_run_version.tsv",
                "/wes/analysis/config.yaml",
                "/wes/analysis/metasheet.csv",
                "/wes/analysis/wes_sample.json",
                "/wes/analysis/tumor_germline_overlap.tsv",
            ]
        ),
        "RNA": FacetConfig(
            [
                "/wes/analysis/vcf_tnscope_filter_neoantigen.vcf",
                "/wes/analysis/haplotyper.vcf.gz",
            ]
        ),
        "MSI": FacetConfig(["/wes/analysis/msisensor.txt"]),
        "Error Documentation": FacetConfig(["/wes/analysis/error.yaml"]),
    },
    "WES Tumor-Only": {
        "TcellExtrect": FacetConfig(["/wes_tumor_only/analysis/tcellextrect.txt"]),
        "Copy Number": FacetConfig(
            [
                "/wes_tumor_only/analysis/copynumber_cnvcalls.txt",
                "/wes_tumor_only/analysis/copynumber_cnvcalls.txt.tn.tsv",
            ]
        ),
        "Error Documentation": FacetConfig(["/wes_tumor_only/analysis/error.yaml"]),
        "Neoantigen": FacetConfig(
            [
                "/wes_tumor_only/analysis/combined_filtered.tsv",
            ]
        ),
        "Somatic": FacetConfig(
            [
                "/wes_tumor_only/analysis/vcf_gz_tnscope_output.vcf.gz",
                "/wes_tumor_only/analysis/maf_tnscope_output.maf",
                "/wes_tumor_only/analysis/vcf_gz_tnscope_filter.vcf.gz",
                "/wes_tumor_only/analysis/maf_tnscope_filter.maf",
                "/wes_tumor_only/analysis/tnscope_exons.vcf.gz",
                "/wes_tumor_only/analysis/tnscope_output_twist.vcf",
                "/wes_tumor_only/analysis/tnscope_output_twist.maf",
                "/wes_tumor_only/analysis/tnscope_output_twist_filtered.vcf",
                "/wes_tumor_only/analysis/tnscope_output_twist_filtered.maf",
            ]
        ),
        "Alignment": FacetConfig(
            [
                "/wes_tumor_only/analysis/tumor/sorted.dedup.bam",
                "/wes_tumor_only/analysis/tumor/sorted.dedup.bam.bai",
            ]
        ),
        "Metrics": FacetConfig(
            [
                "/wes_tumor_only/analysis/tumor/coverage_metrics.txt",
                "/wes_tumor_only/analysis/tumor/target_metrics.txt",
                "/wes_tumor_only/analysis/tumor/coverage_metrics_summary.txt",
            ]
        ),
        "HLA Type": FacetConfig(
            [
                "/wes_tumor_only/analysis/tumor/hla_final_result.txt",
                "/wes_tumor_only/analysis/tumor/optitype_result.tsv",
                "/wes_tumor_only/analysis/tumor/xhla_report_hla.json",
                "/wes_tumor_only/analysis/HLA_results.tsv",
            ]
        ),
        "RNA": FacetConfig(
            [
                "/wes_tumor_only/analysis/vcf_tnscope_filter_neoantigen.vcf",
                "/wes_tumor_only/analysis/haplotyper.vcf.gz",
            ]
        ),
        "Report": FacetConfig(
            [
                "/wes_tumor_only/analysis/report.tar.gz",
                "/wes_tumor_only/analysis/wes_run_version.tsv",
                "/wes_tumor_only/analysis/config.yaml",
                "/wes_tumor_only/analysis/metasheet.csv",
                "/wes_tumor_only/analysis/wes_sample.json",
            ]
        ),
        "MSI": FacetConfig(["/wes_tumor_only/analysis/msisensor.txt"]),
    },
    "RNA": {
        "Source": FacetConfig(
            ["/rna/r1_.fastq.gz", "/rna/r2_.fastq.gz", "/rna/reads_.bam"]
        ),
        "Alignment": FacetConfig(
            [
                "/rna/analysis/star/sorted.bam",
                "/rna/analysis/star/sorted.bam.bai",
                "/rna/analysis/star/sorted.bam.stat.txt",
                "/rna/analysis/star/transcriptome.bam",
                "/rna/analysis/star/chimeric_out_junction.junction",
                "/rna/analysis/star/chimeric_out.junction",
            ]
        ),
        "Quality": FacetConfig(
            [
                "/rna/analysis/rseqc/read_distrib.txt",
                "/rna/analysis/rseqc/tin_score.summary.txt",
                "/rna/analysis/rseqc/tin_score.txt",
            ]
        ),
        "Gene Quantification": FacetConfig(
            [
                "/rna/analysis/salmon/quant.sf",
                "/rna/analysis/salmon/transcriptome.bam.log",
                "/rna/analysis/salmon/aux_info_ambig_info.tsv",
                "/rna/analysis/salmon/aux_info_expected_bias.gz",
                "/rna/analysis/salmon/aux_info_meta_info.json",
                "/rna/analysis/salmon/aux_info_fld.gz",
                "/rna/analysis/salmon/aux_info_observed_bias.gz",
                "/rna/analysis/salmon/aux_info_observed_bias_3p.gz",
                "/rna/analysis/salmon/cmd_info.json",
                "/rna/analysis/salmon/salmon_quant.log",
            ]
        ),
        "Microbiome": FacetConfig(
            [
                "/rna/analysis/microbiome/addSample_report.txt",
                "/rna/analysis/microbiome/sample_report.txt",
            ]
        ),
        "Immune-Repertoire": FacetConfig(["/rna/analysis/trust4/trust4_report.tsv"]),
        "Fusion": FacetConfig(["/rna/analysis/fusion/fusion_predictions.tsv"]),
        "MSI": FacetConfig(
            [
                "/rna/analysis/msisensor/msisensor_report.txt",
                "/rna/analysis/msisensor/msisensor.txt",
            ]
        ),
        "HLA": FacetConfig(["/rna/analysis/neoantigen/genotype.json"]),
    },
    "MIBI": {
        "Metadata Sheet": FacetConfig(
            ["/mibi/metadata.tsv"],
            "TSV-formatted table containing metadata about the run",
        ),
        "Multichannel OME TIFFs": FacetConfig(
            ["/mibi/multichannel_image.ome.tiff"],
            "Analysis-ready multilayer OME-TIFF image file",
        ),
        "Segmentation Masks": FacetConfig(
            ["/mibi/cluster_labels.tif"],
            "TIF-formatted whole cell segmentation masks for each multiplexed image",
        ),
        "Channel Names": FacetConfig(
            ["/mibi/channel_names.csv"],
            "CSV-formatted table of each channel and the corresponding mass",
        ),
        "Single-cell Data": FacetConfig(
            ["/mibi/single_cell_table.csv"],
            "Single cell data table containing eg integrated expression values, XY location",
        ),
    },
    "mIF": {
        "Source Images": FacetConfig(
            [
                "/mif/roi_/composite_image.tif",
                "/mif/roi_/component_data.tif",
                "/mif/roi_/multispectral.im3",
            ],
            "Image files containing the source multi-dimensional images for both ROIs and whole slide if appropriate.",
        ),
        "Images with Features": FacetConfig(
            [
                "/mif/roi_/image_with_all_seg.tif",
                "/mif/roi_/image_with_cell_seg_map.tif",
                "/mif/roi_/image_with_phenotype_map.tif",
                "/mif/roi_/image_with_tissue_seg.tif",
            ],
            "Image files containing the source image and another feature.",
        ),
        "Analysis Images": FacetConfig(
            ["/mif/roi_/binary_seg_maps.tif", "/mif/roi_/phenotype_map.tif"],
            "Image-like files created or used in the analysis workflow. These include cell and region segmentation maps.",
        ),
        "Analysis Data": FacetConfig(
            [
                "/mif/roi_/score_data_.txt",
                "/mif/roi_/cell_seg_data.txt",
                "/mif/roi_/cell_seg_data_summary.txt",
                "/mif/roi_/tissue_seg_data.txt",
                "/mif/roi_/tissue_seg_data_summary.txt",
            ],
            "Data files from image analysis software indicating the cell type assignments, phenotypes and other scoring metrics and thresholds.",
        ),
        "QC Info": FacetConfig(
            ["/mif/qc_report.zip"],
            "Spreadsheets containing info regarding Quality Control from pathology and reasoning for expected failures.",
        ),
    },
    "Olink": {
        "Run-Level": FacetConfig(
            [
                "/olink/batch_/chip_/assay_npx.xlsx",
                "/olink/batch_/chip_/assay_raw_ct.csv",
            ],
            "Analysis files for a single run on the Olink platform.",
        ),
        "Batch-Level": FacetConfig(
            ["/olink/batch_/combined_npx.xlsx"],
            "Analysis files for a batch of runs on the Olink platform",
        ),
        "Study-Level": FacetConfig(
            ["/olink/study_npx.xlsx", "npx|analysis_ready|csv"],
            "Analysis files for all samples run on the Olink platform in the trial.",
        ),
    },
    "IHC": {
        "Images": FacetConfig(["/ihc/ihc_image."]),
        "Combined Markers": FacetConfig(["csv|ihc marker combined"]),
    },
    "H&E": {
        "Images": FacetConfig(
            ["/hande/image_file.svs", "/hande/image_file."], "Stained image file."
        )
    },
    "TCR": {
        "Source": FacetConfig(
            [
                "/tcr/reads.tsv",
                "/tcr/controls/reads.tsv",
                "/tcr/replicate_/r1.fastq.gz",
                "/tcr/replicate_/r2.fastq.gz",
                "/tcr/replicate_/i1.fastq.gz",
                "/tcr/replicate_/i2.fastq.gz",
            ]
        ),
        "Misc.": FacetConfig(
            ["/tcr/SampleSheet.csv", "/tcr_analysis/summary_info.csv"]
        ),
        "Analysis Data": FacetConfig(
            ["/tcr_analysis/tra_clone.csv", "/tcr_analysis/trb_clone.csv"],
            "Data files indicating TRA & TRB clones' UMI counts",
        ),
        "Reports": FacetConfig(
            ["/tcr_analysis/report_trial.tar.gz"], "Report from TCRseq analysis"
        ),
    },
    "ELISA": {"Data": FacetConfig(["/elisa/assay.xlsx"])},
    "ctDNA": {
        "Demultiplexed Source BAMs": FacetConfig(
            ["/ctdna/demultiplexed.bam", "/ctdna/demultiplexed.bam.bai"],
            "Demultiplexed BAM files (and indexes) generated from circulating tumor DNA.",
        ),
        "Genome-wide Plots": FacetConfig(
            ["/ctdna/genome-wide_plots.pdf"],
            "Plots showing Copy Number Alteration (CNA) across the whole genome for all solutions generated by ichorCNA.",
        ),
        "Bias / QC Plots": FacetConfig(
            ["/ctdna/bias_qc_plots.pdf"],
            "Plots showing readcount corrections applied by ichorCNA for GC bias and Mappability bias.",
        ),
        "Optimal Solutions": FacetConfig(
            ["/ctdna/optimal_solution.zip"],
            "The optimal solution as calculated by ichorCNA.",
        ),
        "Other Solutions": FacetConfig(
            ["/ctdna/other_solutions.zip"],
            "Other possible solutions also calculated by ichorCNA.",
        ),
        "Batch-level Summary Plots": FacetConfig(
            ["/ctdna/summary_plots.pdf"],
            "Plots showing Copy Number Alteration (CNA) across the whole genome for each sample for the top 2 solutions generated by ichorCNA.",
        ),
    },
    "Microbiome": {
        "Source": FacetConfig(
            [
                "/microbiome/forward.fastq.gz",
                "/microbiome/forward_index.fastq.gz",
                "/microbiome/reverse.fastq.gz",
                "/microbiome/reverse_index.fastq.gz",
            ]
        ),
        "OTU Tables": FacetConfig(
            ["/microbiome/otu_table.tsv"],
            "Operational taxonomic unit matrix.",
        ),
        "Batch-level Summary Plots": FacetConfig(
            ["/microbiome/summary.pdf"],
            "Plots showing analysis summary for microbiome.",
        ),
    },
}

clinical_facets: Facets = {
    "Participants Info": FacetConfig(["csv|participants info"]),
    "Samples Info": FacetConfig(["csv|samples info"]),
    "Clinical Data": FacetConfig(
        ["/clinical/."],
        "Files containing clinical data supplied by the trial team.",
    ),
}

analysis_ready_facets = {
    "Olink": FacetConfig(["npx|analysis_ready|csv"]),
    "CyTOF": FacetConfig(
        [
            "csv|cell counts assignment",
            "csv|cell counts compartment",
            "csv|cell counts profiling",
        ],
        "Summary cell counts, combined across all samples in the trial",
    ),
    "IHC": FacetConfig(["csv|ihc marker combined"]),
    "Nanostring": FacetConfig(
        ["/nanostring/normalized_data.csv"],
        "Tabulated data across all samples in a batch",
    ),
    "RNA": FacetConfig(
        [
            "/rna/analysis/star/sorted.bam",
            "/rna/analysis/star/sorted.bam.bai",
            "/rna/analysis/star/sorted.bam.stat.txt",
            "/rna/analysis/star/transcriptome.bam",
            "/rna/analysis/star/chimeric_out_junction.junction",
            "/rna/analysis/star/chimeric_out.junction",
            "/rna/analysis/rseqc/read_distrib.txt",
            "/rna/analysis/rseqc/tin_score.summary.txt",
            "/rna/analysis/rseqc/tin_score.txt",
            "/rna/analysis/salmon/quant.sf",
            "/rna/analysis/salmon/transcriptome.bam.log",
            "/rna/analysis/salmon/aux_info_ambig_info.tsv",
            "/rna/analysis/salmon/aux_info_expected_bias.gz",
            "/rna/analysis/salmon/aux_info_meta_info.json",
            "/rna/analysis/salmon/aux_info_fld.gz",
            "/rna/analysis/salmon/aux_info_observed_bias.gz",
            "/rna/analysis/salmon/aux_info_observed_bias_3p.gz",
            "/rna/analysis/salmon/cmd_info.json",
            "/rna/analysis/salmon/salmon_quant.log",
            "/rna/analysis/microbiome/addSample_report.txt",
            "/rna/analysis/microbiome/sample_report.txt",
            "/rna/analysis/trust4/trust4_report.tsv",
            "/rna/analysis/fusion/fusion_predictions.tsv",
            "/rna/analysis/msisensor/msisensor_report.txt",
            "/rna/analysis/msisensor/msisensor.txt",
            "/rna/analysis/neoantigen/genotype.json",
        ]
    ),
    "WES Analysis": FacetConfig(["/wes/analysis/report.tar.gz"]),
    "TCR": FacetConfig(["/tcr_analysis/report_trial.tar.gz"]),
    "mIF": FacetConfig(["/mif/roi_/cell_seg_data.txt"]),
}

facets_dict: Dict[str, Facets] = {
    "Assay Type": assay_facets,
    "Clinical Type": clinical_facets,
    "Analysis Ready": analysis_ready_facets,
}


FACET_NAME_DELIM = "|"


def _build_facet_groups_to_names():
    """Map facet_groups to human-readable data categories."""
    path_to_name = lambda path: FACET_NAME_DELIM.join(path)

    facet_names = {}
    for facet_name, subfacet in facets_dict["Assay Type"].items():
        for subfacet_name, subsubfacet in subfacet.items():
            for facet_group in subsubfacet.facet_groups:
                facet_names[facet_group] = path_to_name([facet_name, subfacet_name])

    for facet_name, subfacet in facets_dict["Clinical Type"].items():
        for facet_group in subfacet.facet_groups:
            facet_names[facet_group] = path_to_name([facet_name])

    # Note on why we don't use "Analysis Ready": any facet group included in the
    # "Analysis Ready" facet type will also have an entry in "Assay Type".
    # The "Assay Type" config will yield a more specific data category for
    # the given facet group, so we skip the "Analysis Ready" config here.

    return facet_names


facet_groups_to_categories = _build_facet_groups_to_names()


def build_data_category_facets(facet_group_file_counts: Dict[str, int]):
    """
    Add file counts by data category into the facets defined in the `facets_dict`,
    and reformat `FacetConfig`s as facet specification dictionaries with the following structure:
    ```python
    {
        "label": <the display name for this facet>,
        "description": <background info for this facet>,
        "count": <number of files related to this facet>
    }
    ```
    """
    extract_facet_info = lambda facet_config_entries, prefix: [
        {
            "label": label,
            "description": config.description,
            "count": sum(
                facet_group_file_counts.get(facet_group, 0)
                for facet_group in config.facet_groups
            ),
        }
        for label, config in facet_config_entries.items()
    ]

    return {
        "Assay Type": {
            assay_name: extract_facet_info(subfacets, assay_name)
            for assay_name, subfacets in assay_facets.items()
        },
        "Clinical Type": extract_facet_info(clinical_facets, None),
        "Analysis Ready": extract_facet_info(analysis_ready_facets, None),
    }


def build_trial_facets(trial_file_counts: Dict[str, int]):
    """
    Convert a mapping from trial ids to file counts into a list of facet specifications.
    """
    return [
        {"label": trial_id, "count": count}
        for trial_id, count in trial_file_counts.items()
    ]


def get_facet_groups_for_paths(paths: List[List[str]]) -> List[str]:
    facet_groups: List[str] = []
    for path in paths:
        try:
            assert len(path) in (2, 3)
            facet_config: Any = facets_dict
            for key in path:
                facet_config = facet_config[key]
            assert isinstance(facet_config, FacetConfig)
        except Exception as e:
            raise BadRequest(f"no facet for path {path}")
        facet_groups.extend(facet_config.facet_groups)

    return facet_groups


# helper function to process and prepare each entry for return
def _process_facet(
    assay: str,
    facet_parts: List[str],
    facet_config: FacetConfig,
    facets_to_return: Dict[str, Dict[str, List[str]]],
) -> None:
    full_facet = "|".join(facet_parts)

    if any("analysis" not in f for f in facet_config.facet_groups):
        facets_to_return[assay]["received"].append(full_facet)
    if any("analysis" in f for f in facet_config.facet_groups):
        facets_to_return[assay]["analyzed"].append(full_facet)


# helper function to return UI assay from first-level facet group
def _translate_assay(facet_group: str) -> str:
    assay: str = facet_group.replace("-", "").lower()
    # wes specifics
    if assay == "wes tumoronly":
        assay = "wes_tumor_only"
    elif "wes" in assay:
        assay = "wes"
    return assay


def get_facet_groups_for_links() -> Dict[str, Dict[str, List[str]]]:
    """
    Return all facets grouped by assay
    Added for selecting a whole assay individually when linking from the dashboard.

    The first key is the assay, as returned for *assays* in models/models.py::TrialMetadata.get_summaries static method.
        Note that the UI goes through *non-analysis assays* and checks for a corresponding analysis, so only using the assay.
    The second key is either "received" or "analyzed" as match the UI.
    The values are a list of facets that are associated with each of those assays, including their analysis.
    """
    # make our return structure
    starting_dict = {"received": [], "analyzed": []}
    facets_to_return: dict = defaultdict(lambda: deepcopy(starting_dict))

    # run through all assay facets and put them in the return
    category: str = "Assay Type"
    for first, first_config in facets_dict[category].items():
        assay = _translate_assay(first)
        for facet, facet_config in first_config.items():
            _process_facet(
                assay, [category, first, facet], facet_config, facets_to_return
            )

    # run through all analysis facets and put them in the return
    category: str = "Analysis Ready"
    for facet, facet_config in facets_dict[category].items():
        assay = _translate_assay(facet)
        _process_facet(assay, [category, facet], facet_config, facets_to_return)

    # run through all clinical facets and put them in the return under `clinical_participants`
    # see models/models.py#L1422
    category: str = "Clinical Type"
    for facet, facet_config in facets_dict[category].items():
        # these will all go into received, as none contain "analysis"
        _process_facet(
            "clinical_participants", [category, facet], facet_config, facets_to_return
        )

    # wes specific, use same values for wes_tumor received as for wes_normal received
    # because facets refer to the WHOLE of WES assay, not broken up by sample type
    facets_to_return["wes_tumor_only"]["received"] = facets_to_return["wes"]["received"]

    # convert so that return will throw KeyErrors for missing keys
    return dict(facets_to_return)
