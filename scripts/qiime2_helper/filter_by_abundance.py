"""
Filter AXIOME3 ASV table (.tsv) by relative abundance.
"""
import pandas as pd
import numpy as np
from argparse import ArgumentParser
import sys
import re

def args_parse():
    """
    Parse command line arguments into Python
    """
    parser = ArgumentParser(description = "Script to generate manifest file for qiime2")

    parser.add_argument('--asv', help="""
            Path to asv table (.asv)
            """,
            required=True)

    parser.add_argument('--threshold', help="""
            Retain ASV if at least one of the samples has % abundance greater
            than the threshold. Provide in decimal. [default=0.01]
            """,
            type=float,
            default=0.01)

    parser.add_argument('--output', help="""
            Path to store output as
            """,
            type=str,
            default="abundance_filtered_ASV_table.tsv")

    return parser

def read_table(asv_path):
    """
    Reads ASV table as pandas dataframe.

    Input:
        asv_path: path to AXIOME3 ASV table.
    """
    asv_df = pd.read_csv(asv_path,
                        sep="\t",
                        header=0,
                        comment="#",
                        index_col="rowID")

    return asv_df

def filter_by_abundance(asv_subset, threshold):
    """
    Filter ASV table by % abundance.

    Input:
        asv_subset: pandas dataframe. Read from AXIOME3 ASV table (.tsv).
                    Should have ASV features as rows and Samples and metadata as
                    columns. It should only contain count data (numeric type)
        threshold: threshold to filter by.
    """
    # Calculate % abundance.
    percent_abundance_df = calculate_percent_value(asv_subset)

    # keep ASVs if at least one of the samples has % abundance >= threshold
    asv_to_keep = (percent_abundance_df >= threshold).any(axis=1)

    # Note that original row index should preserved.
    # Will be buggy if row index is reindexed. (add test case for this?)
    filtered = asv_subset.loc[asv_to_keep]

    return filtered

def calculate_percent_value(df):
    """
    Calculates % value per column. (value / column sum)

    Input:
        asv_df: pandas dataframe. Read from AXIOME3 ASV table (.tsv).
                Should have ASV features as rows and Samples and metadata as
                columns.
        df: pandas dataframe.
    """
    # Calculate % value
    percent_val_df = df.apply(lambda x: percent_value_operation(x), axis=0)

    return percent_val_df

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

def subset_df(df, cols):
    """
    Subset specified columns from the dataframe.

    Input:
        df: pandas dataframe
        cols: Columns to drop
    """
    subset = df[cols]
    others = df.drop(cols, axis="columns")

    return subset, others

def merge_df(dropped, asv_filtered, cols_to_insert_at_beginning):
    """
    Merge two dataframes.

    For visualization purpose, insert "Feature ID" in the beginning, and the rest at the end.
    dropped and asv_filtered MUST have same row index.

    Input:
        - dropped: Subset of dataframe dropped from initial table to be added to
            asv_subset.
        - asv_filtered: % abundance filtered df with counts data only.
        - cols_to_insert_at_beginning: subset of columns in "dropped" df that
            are to be inserted at the beginning of asv_subset df.
    """
    # if dropped is empty, return asv_filtered as it is
    if(dropped.empty):
        print("Nothing to merge. Returning as it is")
        return asv_filtered

    # Check if the specified columns exist in dropped df
    for col in cols_to_insert_at_beginning:
        if(col not in dropped.columns):
            raise ValueError("'{col}' column does not exist in dropped df".format(
                col=col
                ))

    # Remove rows from dropped that are not in asv_filtered
    dropped = dropped.loc[asv_filtered.index, ]

    # Columns to insert at the end
    other_cols = [col for col in dropped.columns if col not in
            cols_to_insert_at_beginning]

    # df to combine at the beginning
    insert_at_beginning = dropped[cols_to_insert_at_beginning]
    # df to combine at the end
    insert_at_end = dropped[other_cols]

    # Combine dataframes into one
    df = pd.concat([insert_at_beginning, asv_filtered, insert_at_end], axis=1)

    return df

def clean_taxa(taxa):
    """
    Clean up SILVA taxonomic names

    Input:
        - taxa: list of SILVA taxa names
    """
    new_taxa = [t.replace(";__", "") for t in taxa]
    new_taxa = [re.sub(r";\s*D_[1-9]__metagenome", "", t) for t in new_taxa]
    new_taxa = [t.replace("Ambiguous_taxa", "") for t in new_taxa]
    new_taxa = [re.sub(r';\s*D_[1-9]__uncultured.*', '', t) for t in new_taxa]
    new_taxa = [re.sub(r'\s*D_[0-9]__', '', t) for t in new_taxa]
    new_taxa = [re.sub(r'.*;', '', t) for t in new_taxa]

    return new_taxa


if __name__ == "__main__":
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Read as pandas dataframe
    asv_df = read_table(args.asv)

    # Subset dataframe
    cols_to_drop = ["Feature ID", "Consensus.Lineage", "ReprSequence"]
    dropped, asv_subset = subset_df(asv_df, cols_to_drop)

    # Filter by abundance
    filtered = filter_by_abundance(asv_subset, args.threshold)

    # Merge dataframe
    merged_df = merge_df(dropped, filtered, ["Feature ID"])

    # Save as tsv
    merged_df.to_csv(args.output, sep="\t")
