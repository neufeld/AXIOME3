#!/usr/bin/env python
# summarize_sample_counts.py
# Copyright Jackson M. Tsuji, Neufeld Research Group, 2019
# Creates a tabular summary of the total read counts of all samples in a qiime2 feature table

# Modified by Daniel Min, Neufeld Research Group, 2019

# Imports
import sys
import os
import time
import logging
import argparse

import pandas as pd
# To import QIIME2 Artifacts into Python
from qiime2 import Artifact

# GLOBAL variables
SCRIPT_VERSION = '0.8.1'

# Set up the logger
logging.basicConfig(format="[ %(asctime)s UTC ]: %(levelname)s: %(message)s")
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

def load_qiime2_artifact(feature_table):
    """
    Load the output of QIIME2 DADA2 (QIIME2 feature table artifact) into Python

    ** Will throw errors if the artifact type is NOT FeatureTable[Frequency] **
    You may check Artifact type by checking the "type" property of the Artifact
    object after loading the artifact via 'Artifact.load(artifact)'
    """
    # Make sure input actually exists
    if not(os.path.isfile(feature_table)):
        msg = "Input file '{in_file}' does NOT exist!".format(
                in_file=feature_table)
        raise FileNotFoundError(msg)

    try:
        feature_table_artifact = Artifact.load(feature_table)

        # Check Artifact type
        if(str(feature_table_artifact.type) != "FeatureTable[Frequency]"):
            msg = "Input QIIME2 Artifact is not of the type 'FeatureTable[Frequency]'!"
            raise ValueError(msg)

        feature_table_df = feature_table_artifact.view(pd.DataFrame)

        return feature_table_df
    except ValueError as err:
        logger.error(err)
        raise
    except Exception as err:
        logger.error(err)
        raise

def generate_sample_count(feature_table_df):
    """
    Generate sample counts given feature table dataframe.
    It sums up counts from each "feature"
    """
    # By default, feature table dataframe stores samples as rows, and features
    # as columns.
    feature_table_df['Count'] = feature_table_df.sum(axis=1)

    # Sort 'Count' column in ascending order
    feature_table_df = feature_table_df.sort_values(by=['Count'])

    # Set index name
    feature_table_df.index.name = 'SampleID'

    return feature_table_df

def write_output(sample_count_df, output_filepath, is_verbose=True):
    """
    Write output
    """
    # Write output
    if(output_filepath is None):
        # Write to STDOUT
        logger.info("Writing counts summary file to STDOUT")
        sample_count_df.to_csv(sys.stdout, sep='\t', columns=['Count'])
    else:
        logger.info("Writing counts summary file to " + output_filepath)

        try:
            sample_count_df.to_csv(output_filepath, sep='\t', columns=['Count'])
        except IOError as err:
            msg = "I/O Error: Cannot open the file {f}".format(f=output_filepath)
            logger.error(msg)
            raise
        except Exception as err:
            logger.error(err)
            raise

def write_output_json(sample_count_df, output_filepath, is_verbose=True):
    """
    Write output
    """
    # Write output
    if(output_filepath is None):
        # Write to STDOUT
        logger.info("Writing counts summary file to STDOUT")
        sample_count_df.to_csv(sys.stdout, sep='\t', columns=['Count'])
    else:
        logger.info("Writing counts summary file to " + output_filepath)

        try:
            sample_count_df['Count'].to_json(output_filepath, orient='index')
        except IOError as err:
            msg = "I/O Error: Cannot open the file {f}".format(f=output_filepath)
            logger.error(msg)
            raise
        except Exception as err:
            logger.error(err)
            raise

def write_min_count(min_count_filepath, sample_count_df):
        logger.info("Writing min count to " + min_count_filepath)

        min_count = int(sample_count_df['Count'].min())
        try:
            with open(min_count_filepath, 'w') as min_count_file:
                min_count_file.write(str(min_count) + '\n')
        except IOError as err:
            msg = "I/O Error: Cannot open the file {f}".format(f=min_count_filepath)
            logger.error(msg)
            raise
        except Exception as err:
            logger.error(err)
            raise

def get_sample_count(feature_table_filepath, tsv_output_path, json_output_path):
    """
    Get sample count and save it to a file

    Input:
        - feature_table_filepath: path to feature table QIIME2 artifact.
        - output_filepath: path to save output
    """
    logger.info("Running summarize_sample_counts.py")

    # Load feature table as pandas dataframe
    feature_table_df = load_qiime2_artifact(feature_table_filepath)

    # Generate sample counts
    sample_count_df = generate_sample_count(feature_table_df)

    # Write output
    write_output(sample_count_df, tsv_output_path)
    write_output_json(sample_count_df, json_output_path)

    logger.info("Done!")

def main(args):
    # Set user variables
    input_filepath = args.input_filepath
    output_filepath = args.output_filepath
    min_count_filepath = args.min_count_filepath
    verbose = args.verbose

    # Set logger verbosity
    if verbose is True:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Startup messages
    logger.info("Running " + os.path.basename(sys.argv[0]))
    logger.info("Version: " + SCRIPT_VERSION)
    logger.info("Input filepath: " + input_filepath)
    logger.info("Output filepath: " + output_filepath\
            if output_filepath is not None\
            else "Output filepath: Verbose")
    logger.info("Min count filepath: " + str(min_count_filepath))
    logger.info("Verbose logging: " + str(verbose))

    # Load feature table as pandas dataframe
    feature_table_df = load_qiime2_artifact(input_filepath)

    # Generate sample counts
    sample_count_df = generate_sample_count(feature_table_df)

    # Write output
    write_output(sample_count_df, output_filepath)
    write_output_json(sample_count_df, "test.json")

    # Get min count and write, if desired
    if min_count_filepath is not None:
        write_min_count(min_count_filepath, sample_count_df)

    logger.info(os.path.basename(sys.argv[0]) + ": done.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Creates a tabular summary of the total read counts of all samples in a qiime2 feature table. "
                                                   "Copyright Jackson M. Tsuji, Neufeld Research Group, 2019. "
                                                   "Version: " + SCRIPT_VERSION)
    parser.add_argument('-i', '--input_filepath', required=True, 
                       help = 'The path to the input QZA FeatureTable file.')
    parser.add_argument('-o', '--output_filepath', required=False, default=None, 
                       help = 'The path to the output TSV file. Will write to STDOUT (-) if nothing is provided.')
    parser.add_argument('-m', '--min_count_filepath', required=False,
                        default=None,
                       help = 'Optional path to write a single-line text file with the lowest count value in the dataset.')
    parser.add_argument('-v', '--verbose', required=False, action='store_true',
                       help = 'Enable for verbose logging.')
    command_line_args = parser.parse_args()

    main(command_line_args)
