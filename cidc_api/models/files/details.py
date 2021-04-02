from typing import NamedTuple
from typing_extensions import Literal


FilePurpose = Literal["source", "analysis", "clinical", "miscellaneous"]


class FileDetails(NamedTuple):
    file_purpose: FilePurpose
    short_description: str
    long_description: str


details_dict = {
    # WES
    "/wes/r1_.fastq.gz": FileDetails(
        "source",
        "fastq file of raw Read 1, compressed",
        "The gzipped, FASTQ file that represents the 5' read of paired sequencing. Generated by the sequencing machine defined by the RNA assay this file is associated with.",
    ),
    "/wes/r2_.fastq.gz": FileDetails(
        "source",
        "fastq file of raw Read 2, compressed",
        "The gzipped, FASTQ file that represents the 3' read of paired sequencing. Generated by the sequencing machine defined by the RNA assay this file is associated with.",
    ),
    "/wes/reads_.bam": FileDetails(
        "source",
        "bam file containing both pairs of sequencing libraries",
        "The paired raw reads in the standard BAM binary format, generated from the raw R1 and R2 FASTQ files.",
    ),
    ## see: https://github.com/CIMAC-CIDC/cidc-ngs-pipeline-api/blob/master/wes/wes_output_API.json
    "/wes/analysis/vcfcompare.txt": FileDetails(
        "analysis",
        "plain-text file of overlaps of somatic and germline variants, from VCFtool's vcf-compare",
        "VCFtool's vcf-compare (http://vcftools.sourceforge.net/perl_module.html#vcf-compare) is used to compare somatic and germline variants.  The file shows the number of common variants, somatic only, and germline only variants.",
    ),
    "/wes/analysis/optimalpurityvalue.txt": FileDetails(
        "miscellaneous", "plain-text tumor purity analysis results, from FACETS", ""
    ),
    "/wes/analysis/clonality_pyclone.tsv": FileDetails(
        "analysis", "tab-separated input file for PyClone generated by Sequenza", ""
    ),
    "/wes/analysis/clonality_table.tsv": FileDetails("analysis", "", ""),
    "/wes/analysis/copynumber_cnvcalls.txt": FileDetails(
        "analysis", "plain-text copynumber analysis results, from Sentieon CNV", ""
    ),
    "/wes/analysis/copynumber_cnvcalls.txt.tn.tsv": FileDetails(
        "analysis",
        "tab-separated segmented copynumber variations, from Sentieon CNV",
        "",
    ),
    "/wes/analysis/MHC_Class_I_all_epitopes.tsv": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/MHC_Class_I_filtered_condensed_ranked.tsv": FileDetails(
        "miscellaneous", "", ""
    ),
    "/wes/analysis/MHC_Class_II_all_epitopes.tsv": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/MHC_Class_II_filtered_condensed_ranked.tsv": FileDetails(
        "miscellaneous", "", ""
    ),
    "/wes/analysis/vcf_tnscope_output.vcf": FileDetails(
        "miscellaneous", "vcf file of somatic variants, from Sention's tnscope", ""
    ),
    "/wes/analysis/maf_tnscope_output.maf": FileDetails(
        "miscellaneous",
        "maf file of VEP-annotated somatic variants, from vcf2maf on output of Sention's tnscope",
        "",
    ),
    "/wes/analysis/vcf_tnscope_filter.vcf": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/maf_tnscope_filter.maf": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/tnscope_exons.gz": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/tn_corealigned.bam": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/tn_corealigned.bam.bai": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/HLA_results.tsv": FileDetails("analysis", "", ""),
    "/wes/analysis/combined_filtered.tsv": FileDetails("analysis", "", ""),
    "/wes/analysis/tumor/recalibrated.bam": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/tumor/recalibrated.bam.bai": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/tumor/sorted.dedup.bam": FileDetails(
        "analysis",
        "bam file with deduplicated reads from tumor sample, from Sention's Dedup",
        "",
    ),
    "/wes/analysis/tumor/sorted.dedup.bam.bai": FileDetails(
        "analysis",
        "bam index file with deduplicated reads from tumor sample, from Sention's Dedup",
        "",
    ),
    "/wes/analysis/tumor/haplotyper_targets.vcf.gz": FileDetails("analysis", "", ""),
    "/wes/analysis/normal/haplotyper_targets.vcf.gz": FileDetails("analysis", "", ""),
    "/wes/analysis/normal/recalibrated.bam": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/normal/recalibrated.bam.bai": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/normal/sorted.dedup.bam": FileDetails(
        "analysis",
        "bam file with deduplicated reads from normal sample, from Sention's Dedup",
        "",
    ),
    "/wes/analysis/normal/sorted.dedup.bam.bai": FileDetails(
        "analysis",
        "bam file with deduplicated reads from normal sample, from Sention's Dedup",
        "",
    ),
    "/wes/analysis/tumor/coverage_metrics.txt": FileDetails(
        "analysis",
        "plain-text genome-wide coverage file from tumor sample, from Sentieon's CoverageMetrics",
        "",
    ),
    "/wes/analysis/tumor/target_metrics.txt": FileDetails(
        "analysis",
        "plain-text targeted exome regions coverage file from tumor sample, from Sentieon's CoverageMetrics",
        "",
    ),
    "/wes/analysis/tumor/coverage_metrics_summary.txt": FileDetails(
        "analysis",
        "plain-text genome-wide coverage summary file from tumor sample, from Sentieon's CoverageMetrics",
        "",
    ),
    "/wes/analysis/tumor/target_metrics_summary.txt": FileDetails(
        "analysis",
        "plain-text targeted exome regions coverage summary file from tumor sample, from Sentieon's CoverageMetrics",
        "",
    ),
    "/wes/analysis/tumor/mosdepth_region_dist_broad.txt": FileDetails(
        "miscellaneous", "", ""
    ),
    "/wes/analysis/tumor/mosdepth_region_dist_mda.txt": FileDetails(
        "miscellaneous", "", ""
    ),
    "/wes/analysis/tumor/mosdepth_region_dist_mocha.txt": FileDetails(
        "miscellaneous", "", ""
    ),
    "/wes/analysis/normal/coverage_metrics.txt": FileDetails(
        "analysis",
        "plain-text genome-wide coverage file from normal sample, from Sentieon's CoverageMetrics",
        "",
    ),
    "/wes/analysis/normal/target_metrics.txt": FileDetails(
        "analysis",
        "plain-text targeted exome regions coverage file from normal sample, from Sentieon's CoverageMetrics",
        "",
    ),
    "/wes/analysis/normal/coverage_metrics_summary.txt": FileDetails(
        "analysis",
        "plain-text genome-wide coverage summary file from normal sample, from Sentieon's CoverageMetrics",
        "",
    ),
    "/wes/analysis/normal/target_metrics_summary.txt": FileDetails(
        "analysis",
        "plain-text targeted exome regions coverage summary file from normal sample, from Sentieon's CoverageMetrics",
        "",
    ),
    "/wes/analysis/normal/mosdepth_region_dist_broad.txt": FileDetails(
        "miscellaneous", "", ""
    ),
    "/wes/analysis/normal/mosdepth_region_dist_mda.txt": FileDetails(
        "miscellaneous", "", ""
    ),
    "/wes/analysis/normal/mosdepth_region_dist_mocha.txt": FileDetails(
        "miscellaneous", "", ""
    ),
    "/wes/analysis/tumor/optitype_result.tsv": FileDetails(
        "analysis",
        "plain-text predicted MHC Class I alleles from tumor sample, from OptiType",
        "",
    ),
    "/wes/analysis/normal/optitype_result.tsv": FileDetails(
        "analysis",
        "plain-text predicted MHC Class I alleles from normal sample, from OptiType",
        "",
    ),
    "/wes/analysis/wes_version.txt": FileDetails(
        "miscellaneous", "wes pipeline version- INTERNAL ONLY- for reproducibility", ""
    ),
    # WES Report
    "/wes/analysis/tumor_mutational_burden.tsv": FileDetails("analysis", "", ""),
    "/wes/analysis/report.tar.gz": FileDetails("analysis", "", ""),
    "/wes/analysis/wes_run_version.tsv": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/config.yaml": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/metasheet.csv": FileDetails("miscellaneous", "", ""),
    "/wes/analysis/wes_sample.json": FileDetails("analysis", "", ""),
    "/wes/analysis/xhla_report_hla.json": FileDetails("analysis", "", ""),
    # RNA
    "/rna/r1_.fastq.gz": FileDetails(
        "source",
        "fastq file of raw Read 1, compressed",
        "The gzipped, FASTQ file that represents the 5' read of paired sequencing. Generated by the sequencing machine defined by the RNA assay this file is associated with.",
    ),
    "/rna/r2_.fastq.gz": FileDetails(
        "source",
        "fastq file of raw Read 2, compressed",
        "The gzipped, FASTQ file that represents the 3' read of paired sequencing. Generated by the sequencing machine defined by the RNA assay this file is associated with.",
    ),
    "/rna/reads_.bam": FileDetails(
        "source",
        "bam file containing the paired pairs",
        "The paired raw reads in the standard BAM binary format, generated from the raw R1 and R2 FASTQ files.",
    ),
    ## see: https://github.com/CIMAC-CIDC/cidc-ngs-pipeline-api/blob/master/rna/rna_level1_output_API.json
    "/rna/analysis/star/sorted.bam": FileDetails(
        "analysis",
        "bam file of the aligned reads with index sorted.bam.bai, sorted by their location in the genome from STAR",
        "Aligned reads in the standard BAM binary format, sorted by their coordinate in the genome (similar to `samtools sort`) which is required by many downstream applications.",
    ),
    "/rna/analysis/star/sorted.bam.bai": FileDetails(
        "miscellaneous",
        "bam index file of the aligned reads that accompanies sorted.bam, sorted by their location in the genome from STAR",
        "The index for the aligned reads in the standard BAI binary format, sorted by their coordinate in the genome (similar to `samtools sort`) which is required by many downstream applications.",
    ),
    "/rna/analysis/star/sorted.bam.stat.txt": FileDetails(
        "miscellaneous",
        "plain text statistics of sorted.bam file alignment",
        "A plain-text file of summary statistics of the alignment. Provides informaion useful for determining sample quality and discovering alignment errors.",
    ),
    "/rna/analysis/star/downsampling.bam": FileDetails(
        "miscellaneous",
        "bam file of downsampled aligned reads with index downsampling.bam.bai",
        "A subset of the aligned reads in the standard BAM binary format, sorted by their coordinate in the genome (similar to `samtools sort`). Subsetting is done to speed the quality control done via RSeQC.",
    ),
    "/rna/analysis/star/downsampling.bam.bai": FileDetails(
        "miscellaneous",
        "bam index file of downsampled aligned reads that accompanies downsampling.bam",
        "The index for the subset of the aligned reads in the standard BAI binary format, sorted by their coordinate in the genome (similar to `samtools sort`). Subsetting is done to speed the quality control done via RSeQC.",
    ),
    "/rna/analysis/rseqc/downsampling_housekeeping.bam": FileDetails(
        "miscellaneous",
        "bam file of the downsampled aligned reads of housekeeping genes with index downsampling_housekeeping.bam.bai",
        "A small subset of the reads aligned to housekeeping genes in the standard BAM binary format.",
    ),
    "/rna/analysis/rseqc/downsampling_housekeeping.bam.bai": FileDetails(
        "miscellaneous",
        "bam index file of the downsampled aligned reads of housekeeping genes that accompanies downsampling_housekeeping.bam",
        "The index for the small subset of the reads aligned to housekeeping genes in the standard BAM binary format.",
    ),
    "/rna/analysis/rseqc/read_distrib.txt": FileDetails(
        "clinical",
        "plain-text statistics of the distribution of the aligned reads from RSeQC",
        "A plain-text file containing summary statistics about the overall mapping and rate of alignment for different types of sequence elements, using the downsampled BAM from STAR. Produced by RSeQC.",
    ),
    "/rna/analysis/rseqc/tin_score.summary.txt": FileDetails(
        "miscellaneous",
        "tab-separated statistics of the Transcript Integrity Number (TIN) score calculated for each gene by RSeQC",
        "A two-line tab-separated file containing the mean, median, and stdev of the TIN scores, using the downsampled BAM from STAR. Produced by RSeQC.",
    ),
    "/rna/analysis/rseqc/tin_score.txt": FileDetails(
        "analysis",
        "tab-separated table of Transcript Integrity Number (TIN) scores calculated for each gene by RSeQC",
        "A five-column tab-separated table containing the gene, chromosome, start and end locations, and the TIN score, using the downsampled BAM from STAR. Produced by RSeQC.",
    ),
    "/rna/analysis/salmon/quant.sf": FileDetails(
        "miscellaneous",
        "tab-separated quantification output (columns: Name, Length, EffectiveLength, TPM, NumReads) from Salmon",
        "A plain-text, tab-separated file with a single header line (which names all of the columns). Each subsequent row describes a single quantification record. The columns have the following interpretations:\nName — This is the name of the target transcript provided in the input transcript database (FASTA file).\nLength — This is the length of the target transcript in nucleotides.\nEffectiveLength — This is the computed effective length of the target transcript. It takes into account all factors being modeled that will effect the probability of sampling fragments from this transcript, including the fragment length distribution and sequence-specific and gc-fragment bias (if they are being modeled).\nTPM — This is salmon’s estimate of the relative abundance of this transcript in units of Transcripts Per Million (TPM). TPM is the recommended relative abundance measure to use for downstream analysis.\nNumReads — This is salmon’s estimate of the number of reads mapping to each transcript that was quantified. It is an “estimate” insofar as it is the expected number of reads that have originated from each transcript given the structure of the uniquely mapping and multi-mapping reads and the relative abundance estimates for each transcript. [Salmon documentation].",
    ),
    "/rna/analysis/salmon/transcriptome.bam.log": FileDetails(
        "miscellaneous",
        "the log file produced during processing of the transcriptome by Salmon",
        "A plain-text file containing the time and output of all logging by Salmon during sample preparation of the target transcriptome against which samples can be analysed.",
    ),
    "/rna/analysis/salmon/aux_info_ambig_info.tsv": FileDetails(
        "miscellaneous",
        "tab-separated statistics of ambiguously mapping reads for each transcript from Salmon",
        "A 2-column tab-separated file that contains information about the number of uniquely-mapping reads as well as the total number of ambiguously-mapping reads for each transcript. This file is provided mostly for exploratory analysis of the results; it gives some idea of the fraction of each transcript’s estimated abundance that derives from ambiguously-mappable reads. [Salmon documentation].",
    ),
    "/rna/analysis/salmon/aux_info_expected_bias.gz": FileDetails(
        "miscellaneous",
        "compressed binary file with information about the expected (5') sequence-specific biases from Salmon",
        "A gzipped, binary file that encodes the expected parameters of the VLMM that were learned for the 5' end.\nIt starts with 3x 32-bit signed int that represent length of context window, length left of the read, and length right of the read.\nThen there are 3 arrays of 32-bit signed ints of the length as the context window which represent the order of the VLMM for that position, and the shift and width to extract each subcontext window.\nThen 2x 64-bit signed ints specify the dimension of the table that immediately follow, where each row represents the nonzero probabilities of the VLMM for one subcontext window.\nFinally, the file contains the distribution of nucleotides in each position in the context as a 4-column table preceded by its dimensions as 2x 64-bit signed int.\n[Adapted from Salmon documentation].",
    ),
    "/rna/analysis/salmon/aux_info_meta_info.json": FileDetails(
        "miscellaneous",
        "json file of statistics and meta information about the Salmon run",
        "A JSON format file which contains meta information about the run, including stats such as the number of observed and mapped fragments, details of the bias modeling etc.\nOne particularly important piece of information contained in this file is the inferred library type. Most of the information recorded in this file should be self-descriptive. [Salmon documentation].",
    ),
    "/rna/analysis/salmon/aux_info_observed_bias.gz": FileDetails(
        "miscellaneous",
        "compressed binary file with information about the observed 5' sequence-specific biases from Salmon",
        "A gzipped, binary file that encodes the observed parameters of the VLMM that were learned for the 5' end.\nIt starts with 3x 32-bit signed int that represent length of context window, length left of the read, and length right of the read.\nThen there are 3 arrays of 32-bit signed ints of the length as the context window which represent the order of the VLMM for that position, and the shift and width to extract each subcontext window.\nThen 2x 64-bit signed ints specify the dimension of the table that immediately follow, where each row represents the nonzero probabilities of the VLMM for one subcontext window.\nFinally, the file contains the distribution of nucleotides in each position in the context as a 4-column table preceded by its dimensions as 2x 64-bit signed int.\n[Adapted from Salmon documentation].",
    ),
    "/rna/analysis/salmon/aux_info_observed_bias_3p.gz": FileDetails(
        "miscellaneous",
        "compressed binary file with information about the observed 3' sequence-specific biases from Salmon",
        "A gzipped, binary file that encodes the observed parameters of the VLMM that were learned for the 3' end.\nIt starts with 3x 32-bit signed int that represent length of context window, length left of the read, and length right of the read.\nThen there are 3 arrays of 32-bit signed ints of the length as the context window which represent the order of the VLMM for that position, and the shift and width to extract each subcontext window.\nThen 2x 64-bit signed ints specify the dimension of the table that immediately follow, where each row represents the nonzero probabilities of the VLMM for one subcontext window.\nFinally, the file contains the distribution of nucleotides in each position in the context as a 4-column table preceded by its dimensions as 2x 64-bit signed int.\n[Adapted from Salmon documentation].",
    ),
    "/rna/analysis/salmon/cmd_info.json": FileDetails(
        "miscellaneous",
        "json file that records the command parameters used to call Salmon",
        "A JSON format file that records the main command line parameters with which Salmon was invoked for the run that produced the output in this directory. [Salmon documentation].",
    ),
    "/rna/analysis/salmon/salmon_quant.log": FileDetails(
        "miscellaneous",
        "the log file produced by the Salmon analysis",
        "A plain-text file containing the time and output of all logging by Salmon during sample analysis.",
    ),
    # Nanostring
    "/nanostring/.rcc": FileDetails(
        "source",
        "xml-encoded comma-separated direct outputs from a NanoString sample",
        "A plain-text XML file with comma-separated table elements for the raw NanoString output from a sample.",
    ),
    "/nanostring/control.rcc": FileDetails(
        "source",
        "xml-encoded csv direct outputs from a NanoString control",
        "A plain-text XML file with comma-separated table elements for the raw NanoString output from a control.",
    ),
    "/nanostring/raw_data.csv": FileDetails(
        "analysis",
        "comma-separated values aggregated from the raw RCC files for all samples/controls",
        "A comma-separated file where each column represents the values pulled from a sample/control's RCC file.",
    ),
    "/nanostring/normalized_data.csv": FileDetails(
        "analysis",
        "comma-separated values aggregated for all samples/controls and normalized",
        "A comma-separated file where each column is the normalized values for a sample/control.",
    ),
    # mIF
    "/mif/roi_/composite_image.tif": FileDetails(
        "source",
        "tiff image of region-of-interest merging all of the signals into a single image",
        "The TIFF image of the region-of-interest that contains the composition of all components into a combined image. Exported from inForm (PerkinElmer).",
    ),
    "/mif/roi_/component_data.tif": FileDetails(
        "source",
        "multi-image tiff of region-of-interest holding all of the individual component signals",
        "The multi-image TIFF of the region-of-interest that contains all of the individual components, one for each marker. Exported from inForm (PerkinElmer).",
    ),
    "/mif/roi_/multispectral.im3": FileDetails(
        "source",
        "multispectral image in the PerkinElmer IM3 format",
        "The multispectral image of the region-of-interest taken by Mantra, in the PerkinElmer IM3 file format. Used as input for inForm.",
    ),
    "/mif/roi_/binary_seg_maps.tif": FileDetails(
        "analysis",
        "multi-image tiff of region-of-interest holding all maps as binary in/out, from inForm",
        "A multi-image TIFF of the region-of-interest, all Tissue, Cell, and Object maps created in analysis are stored as binary in/out 'images', as well as any processing maps. Exported from inForm (PerkinElmer).",
    ),
    "/mif/roi_/phenotype_map.tif": FileDetails(
        "analysis",
        "tiff image where each dot is a phenotyped cell, from inForm",
        "A TIFF image using dots to represent the location of each cell in the region-of-interest with each called phenotype in a different color. Exported from inForm (PerkinElmer).",
    ),
    "/mif/roi_/score_data_.txt": FileDetails(
        "analysis",
        "plain-text statistics on the score step, from inForm",
        "A plain-text file containing at mimimum, 'Tissue Category' and 'Area (Percent)', 'Number of cells', 'Cell Compartment', 'Stain Component'. Exported from inForm (PerkinElmer).",
    ),
    "/mif/roi_/cell_seg_data.txt": FileDetails(
        "analysis",
        "tab-separated statistics on each cell in the region-of-interest, from inForm",
        "A wide tab-separated file containing information and statistics on each cell in the range of interest. For each cell, measures of its position, size, shape, and marker expression in several compartments are recorded. Exported from inForm (PerkinElmer).",
    ),
    "/mif/roi_/cell_seg_data_summary.txt": FileDetails(
        "analysis",
        "tab-separated statistics of cells, summarized across each phenotype in the region-of-interest, from inForm",
        "A wide tab-separated file containing information and statistics across all cells of a given phenotype in the region-of-interest. Contains the same measures of position, size, shape and marker expression in several compartments as does the cell_seg_data file. Exported from inForm (PerkinElmer).",
    ),
    # Olink
    "Assay Type|Olink|All Olink Files|/olink": FileDetails(
        "miscellaneous",
        "any olink file",
        "A file generated in relation to an Olink study.",
    ),
    "/olink/study_npx.xlsx": FileDetails(
        "source",
        "excel file that has the Normalized Protein eXpression results for the full study",
        "An XML-based Excel file that contains the combined results across the full study in Log2-scaled NPX, or Normalized Protein eXpression (Olink’s arbitrary unit). NPX is calculated from Ct values and data pre-processing (normalization) is performed to minimize both intra- and inter-assay variation.\nNPX data allows users to identify changes for individual protein levels across their sample set, and then use this data to establish protein signatures.",
    ),
    "/olink/batch_/combined_npx.xlsx": FileDetails(
        "source",
        "excel file that has the Normalized Protein eXpression results for a batch of samples",
        "An XML-based Excel file that contains the combined results across a batch of samples in Log2-scaled NPX, or Normalized Protein eXpression (Olink’s arbitrary unit). NPX is calculated from Ct values and data pre-processing (normalization) is performed to minimize both intra- and inter-assay variation.\nNPX data allows users to identify changes for individual protein levels across their sample set, and then use this data to establish protein signatures.",
    ),
    "/olink/batch_/chip_/assay_npx.xlsx": FileDetails(
        "source",
        "excel file that has the Normalized Protein eXpression results for a single chip",
        "An XML-based Excel file that contains the results from a single chip in Log2-scaled NPX, or Normalized Protein eXpression (Olink’s arbitrary unit). Combined with other chips in study_npx.xlsx.\nNPX is calculated from Ct values and data pre-processing (normalization) is performed to minimize both intra- and inter-assay variation.\nNPX data allows users to identify changes for individual protein levels across their sample set, and then use this data to establish protein signatures.",
    ),
    "/olink/batch_/chip_/assay_raw_ct.csv": FileDetails(
        "source",
        "comma-separated table of Ct values results for a single chip",
        "The comma-separated, plain-text table that contains the raw Ct value results from a single chip. These values are not normalized for intra- or inter-assay variablity, and a high Ct value is related to a low protein concentration.",
    ),
    "npx|analysis_ready|csv": FileDetails(
        "analysis",
        "comma-separated table of Normalized Protein eXpressions for for all analytes/samples across the entire study",
        "The comma-separated, plain-text table of Normalized Protein eXpressions for all samples (valid CIMAC ID) and analytes (have Olink ID) across the entire study.\nEach row is a sample by CIMAC ID and each column is a sample by (Name, Uniprot ID, *Olink ID*).\nNote that quality control columns and non-sample rows have been removed.",
    ),
    # IHC
    "/ihc/ihc_image.": FileDetails(
        "source",
        "image file that is the result of an IHC experiment",
        "The image file generated from an IHC experiment. Generally, higher signal relates to higher local concentrations of protein, allowing for inferences of both tissue- and cell-level localization.",
    ),
    "csv|ihc marker combined": FileDetails(
        "analysis",
        "comma-separated quantification file of IHC image for all markers",
        "A comma-separated file containing quantification of each marker from the corresponding IHC image.",
    ),
    # Clinical
    "csv|participants info": FileDetails("clinical", "", ""),
    "csv|samples info": FileDetails("clinical", "", ""),
    # TCR
    "/tcr/replicate_/r1.fastq.gz": FileDetails("source", "", ""),
    "/tcr/replicate_/r2.fastq.gz": FileDetails("source", "", ""),
    "/tcr/replicate_/i1.fastq.gz": FileDetails("source", "", ""),
    "/tcr/replicate_/i2.fastq.gz": FileDetails("source", "", ""),
    "/tcr/SampleSheet.csv": FileDetails("miscellaneous", "", ""),
    "/tcr/summary_info.csv": FileDetails("miscellaneous", "", ""),
    "/tcr/tra_clone.csv": FileDetails("analysis", "", ""),
    "/tcr/trb_clone.csv": FileDetails("analysis", "", ""),
    # H&E
    "/hande/image_file.svs": FileDetails(
        "source",
        "stained image file that is the result of an H&E experiment",
        "An SVS image file stained with hematoxylin and eosin, generated from an H&E experiment.",
    ),
    # ELISA
    "/elisa/assay.xlsx": FileDetails(
        "source",
        "xlsx file of measured values where rows are samples and columns are antigens",
        "An XML-based Excel file that contains the results of a single run in arbitrary units. Each row is a sample, though not all have CIMAC IDs, and each column is an antigen.",
    ),
}

# handle CyTOF separately to use same FacetConfig definitions for all versions
for version in ["cytof_10021", "cytof_e4412"]:
    details_dict.update(
        {
            f"/{version}/spike_in.fcs": FileDetails(
                "source",
                "normalized and debarcoded fcs data for a blank spike-in sample",
                "The FCS file that captures pure spike-in for use as a control, after normalization and debarcoding.",
            ),
            f"/{version}/source_.fcs": FileDetails(
                "source",
                "raw fcs data as generated by the machine, without normalization, debarcoding, or cleaning",
                "The raw FCS file as generated by the machine, without any normalization, debarcoding, cleaning, etc.",
            ),
            f"/{version}/normalized_and_debarcoded.fcs": FileDetails(
                "source",
                "normalized and debarcoded fcs data, without cleaning",
                "The FCS file after normalization and debarcoding, but without Veri-Cells and other non-specimen cells removed.",
            ),
            f"/{version}/processed.fcs": FileDetails(
                "source",
                "fully processed fcs data: normalized, debarcoded, no Veri-Cells, cleaned",
                "The analysis-ready FCS file after normalization, debarcoding, and removal of Veri-Cells and other non-specimen cells.",
            ),
            f"/{version}_analysis/cell_counts_assignment.csv": FileDetails(
                "analysis",
                "comma-separated two-column table with cell counts for each assigned cell type",
                "A plain-text, comma-separated table with a numbered index column, the 'CellSubset' as the called cell type, and 'N', the number of cells of that type seen in the sample.",
            ),
            f"/{version}_analysis/cell_counts_compartment.csv": FileDetails(
                "analysis",
                "comma-separated two-column table with cell counts for each broad compartment assigned",
                "A plain-text, comma-separated table with a numbered index column, the 'CellSubset' as the broad compartment of the called cell types, and 'N', the number of cells within that compartment seen in the sample.",
            ),
            f"/{version}_analysis/cell_counts_profiling.csv": FileDetails(
                "analysis",
                "comma-separated two-column table with cell counts for each profiled subset of all assigned cell types",
                "A plain-text, comma-separated table with a numbered index column, the 'CellSubset' as the profiled subset of the assigned cell types, and 'N', the number of cells within that profiled subset seen in the sample.",
            ),
            f"/{version}_analysis/assignment.csv": FileDetails(
                "analysis",
                "comma-separated table of marker expression for each assigned cell type",
                "A plain-text, comma-separated table with a column for each assigned cell type, where rows are the signal on each channel for every cell type assigned.",
            ),
            f"/{version}_analysis/compartment.csv": FileDetails(
                "analysis",
                "comma-separated table of marker expression for each broad compartment assigned",
                "A plain-text, comma-separated table with a column for each broad compartment of the called cell types, where rows are the signal on each channel for every compartment.",
            ),
            f"/{version}_analysis/profiling.csv": FileDetails(
                "analysis",
                "comma-separated table of marker expression for each profiled subset of all assigned cell types",
                "A plain-text, comma-separated table with a column for each profiled subset of all assigned cell types, where rows are the signal on each channel for every profiled subset.",
            ),
            f"/{version}_analysis/source.fcs": FileDetails(
                "source",
                "fcs data used as the input for this analysis",
                "The analysis-ready FCS file used as the input for this analysis. After normalization, debarcoding, and removal of Veri-Cells and other non-specimen cells.",
            ),  # schemas/assays/components/cytof/cytof_analysis.json#properties/fcs_file
        }
    )
