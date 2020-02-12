from qiime2 import Artifact
from argparse import ArgumentParser
import pandas as pd
import sys

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

def convert(artifact_path, output_path):
    artifact = Artifact.load(artifact_path)
    artifact_type = str(artifact.type)

    if(artifact_type == "FeatureTable[Frequency]"):
        df = artifact.view(pd.DataFrame)

        df.to_csv(output_path, sep='\t')

if __name__ == '__main__':
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Convert QIIME2 artifact and export it as csv
    convert(args.artifact_path, args.output_path)
