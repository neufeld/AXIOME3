from qiime2 import Artifact
from argparse import ArgumentParser
import pandas as pd
from skbio.stats import ordination
import sys
import logging

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

if __name__ == '__main__':
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Convert QIIME2 artifact and export it as csv
    convert(args.artifact_path, args.output_path)
