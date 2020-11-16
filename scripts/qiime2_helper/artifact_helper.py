import pandas as pd
import numpy as np
import re
import sys
import logging
import glob
import os

from qiime2 import Artifact, Metadata
from argparse import ArgumentParser
from skbio.stats import ordination

# Custom exception
from exceptions.exception import AXIOME3Error
from scripts.qiime2_helper.q2_artifact_types import ARTIFACT_TYPES

# Define constants
# Taxa collapse valid levels
VALID_COLLAPSE_LEVELS = {
    "domain": 1, 
    "phylum": 2,
    "class": 3,
    "order": 4, 
    "family": 5, 
    "genus": 6, 
    "species": 7,
    "asv": 8
}

logger = logging.getLogger(__name__)

def args_parse():
    """
    Parse command line arguments into Python
    """
    parser = ArgumentParser(description = "Script to generate manifest file for qiime2")

    parser.add_argument('--artifact-path', help="""
            Path to QIIME2 Artifact.
            """,
            required=True)

    parser.add_argument('--output-path', help="""
            Path to store output as
            """,
            type=str,
            required=True)

    return parser

def convert(artifact_path):
    """
    Converts QIIME2 artifact to tsv if applicabl if applicable

    Input:
        - artifact_path: path to QIIME2 artifact (.qza)
        - output_path: path to save output as
    Returns:
        - Dictionary with pandas series or dataframe as values
    """
    artifact = Artifact.load(artifact_path)
    artifact_type = str(artifact.type)

    if(artifact_type == "FeatureTable[Frequency]" or
        artifact_type == "FeatureTable[RelativeFrequency]"):
        df = artifact.view(pd.DataFrame)

        output = {
                "feature_table": df
                }

        return output
    elif(artifact_type == "PCoAResults"):
        ordination_result = artifact.view(ordination.OrdinationResults)

        eigvals = ordination_result.eigvals # pd.DataFrame
        coordinates = ordination_result.samples # pd.Series
        proportion_explained = ordination_results.proportion_explained # pd.Series 

        output = {
                "eigvals": eigvals,
                "coordinates": coordinates,
                "proportion_explained": proportion_explained
                }

        return output
    else:
        logger.warning("Could not convert specified QIIME2 artifact.")
        return {}

def check_artifact_type(artifact_path, artifact_type):
    q2_artifact = Artifact.load(artifact_path)

    # Raise ValueError if not appropriate type
    if(str(q2_artifact.type) != ARTIFACT_TYPES[artifact_type]):
        msg = "Input QIIME2 Artifact is not of the type '{}'".format(ARTIFACT_TYPES[artifact_type])
        raise AXIOME3Error(msg)

    return q2_artifact

def rename_taxa(taxa, row_id):

    def rename_taxa_silva132(taxa, row_id):
        """
        Clean up SILVA132 taxonomic names

        Input:
        - taxa: list of SILVA taxa names (pd.Series)
        - row_id: row ID (pd.Series)
        """
        taxa_with_id = taxa.astype(str) + "_" + row_id.astype(str)
        #taxa_with_id = taxa.astype(str)

        new_taxa = [t.replace(';__', '') for t in taxa_with_id]
        #new_taxa = [re.sub(r";\s*Ambiguous_taxa", "", t) for t in taxa_with_id]
        #new_taxa = [re.sub(r"(;\s*D_[2-6]__uncultured[^;_0-9]*)", "", t) for t in new_taxa]
        new_taxa = [re.sub(r"\s*D_[0-6]__", "", t) for t in new_taxa]

        # get the last entry
        new_taxa = [re.sub(r".*;", "", t) for t in new_taxa]

        return new_taxa

    def rename_taxa_silva138(taxa, row_id):
        """
        Clean up SILVA138 taxonomic names

        Input:
        - taxa: list of SILVA taxa names (pd.Series)
        - row_id: row ID (pd.Series)
        """
        taxa_with_id = taxa.astype(str) + "_" + row_id.astype(str)
        #taxa_with_id = taxa.astype(str)

        new_taxa = [t.replace(';__', '') for t in taxa_with_id]
        #new_taxa = [re.sub(r";\s*Ambiguous_taxa", "", t) for t in taxa_with_id]
        #new_taxa = [re.sub(r"(;\s*[dpcofgs]__uncultured[^;dpcofgs]*)", "", t) for t in new_taxa]
        new_taxa = [re.sub(r"\s*[dpcofgs]__", "", t) for t in new_taxa]

        # get the last entry
        new_taxa = [re.sub(r".*;", "", t) for t in new_taxa]

        return new_taxa

    # Determine whether given taxa name is SILVA132 or 138
    # 132 format has D_[0-6] prefix
    if(taxa.str.contains('D_[0-6]', regex=True).any()):
        return rename_taxa_silva132(taxa, row_id)
    else:
        return rename_taxa_silva138(taxa, row_id)

def filter_by_abundance(df, abundance_threshold=0.1, percent_axis=0, filter_axis=1):
    """
    Calculates taxa percent abundance per sample. (taxa abundance / overall abundance in a sample).

    Input:
        - df: pandas dataframe describing taxa/ASV abundance per sample.
        - abundance_threshold: % value threshold (0: 0% cutoff, 1: 100% cutoff)
        - percent_axis: axis used to calculate % abundance
        - filter_axis: axis used to filter (filter if at least one of the samples has % abundance >= threshold)

        If samples as columns, and taxa/ASV as rows, do percent_axis=0, filter_axis=1.
        If samples as rows, and taxa/ASV as columns, do percent_axis=1, filter_axis=0.

        Default options assume samples as columns and taxa/ASV as rows.
    """
    percent_df = calculate_percent_value(df, percent_axis)

    # keep taxa/ASVs if at least one of the samples has % abundance >= threshold
    to_keep = (percent_df >= abundance_threshold).any(filter_axis)

    # Raise error if no entries after filtering?
    if(to_keep.any() == False):
        raise AXIOME3Error("Zero entries after filtering by abundance at {} threshold".format(abundance_threshold))

    # Note that original row index should preserved.
    # Will be buggy if row index is reindexed. (add test case for this?)
    filtered = df.loc[to_keep, ]

    return filtered

def calculate_percent_value(df, axis=0):
    """
    (value / column (row) sum)
    Column by default.
    """

    def percent_value_operation(x):
        """
        Custom function to be applied on pandas dataframe.

        Input:
                x: pandas series; numerical data
        """
        series_length = x.size
        series_sum = x.sum()

        # percent value should be zero if sum is 0
        all_zeros = np.zeros(series_length)
        percent_values = x / series_sum if series_sum != 0 else pd.Series(all_zeros)

        return percent_values

    # Calculate % value
    percent_val_df = df.apply(lambda x: percent_value_operation(x), axis=axis)

    return percent_val_df

def combine_dada2_stats_as_df(dada2_dir):
    """
    Combines multiple stats.qza as pandas dataframe
    """
    pattern = os.path.join(dada2_dir, '**/*stats_dada2.qza')
    stats_list = glob.glob(pattern, recursive=True)

    stats_df = [Artifact.load(f).view(Metadata).to_dataframe() for f in stats_list]
    combined_stats = pd.concat(stats_df)

    return combined_stats

def import_dada2_stats_df_to_q2(df):
    combined_artifact = Artifact.import_data("SampleData[DADA2Stats]", Metadata(df))

    return combined_artifact

if __name__ == '__main__':
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Convert QIIME2 artifact and export it as csv
    convert(args.artifact_path, args.output_path)
