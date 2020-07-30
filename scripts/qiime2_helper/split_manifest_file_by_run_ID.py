#!/usr/bin/env python
# split_manifest_file_by_run_ID.py
# Copyright Jackson M. Tsuji, Neufeld Research Group, 2019
# Simple script to split a QIIME2 manifest file into multiple files based on the run_ID column

# Imports
import sys
import os
import time
import logging
import argparse

import pandas as pd

# Custom exception
from exceptions.exception import AXIOME3Error

# GLOBAL VARIABLES
SCRIPT_VERSION = '0.8.0'

# Set up the logger
logging.basicConfig(level=logging.INFO, format="[ %(asctime)s UTC ]: %(levelname)s: %(module)s: %(message)s")
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

def split_manifest(manifest_path, output_dir):
    manifest_df = pd.read_csv(manifest_path)

    if ('run_ID' not in manifest_df.columns):
        raise AXIOME3Error("'run_ID' column must exist in the manifes file!")

    # Get unique run IDs
    unique_run_IDs = manifest_df['run_ID'].unique()

    # Split table and write
    for run_ID in unique_run_IDs:
        output_filename = "manifest_" + str(run_ID) + ".csv"
        output_filepath = os.path.join(output_dir, output_filename)
        
        single_run_table = manifest_df[manifest_df['run_ID'] == run_ID]
        # Drop run_ID column
        single_run_table = single_run_table.drop(['run_ID'], axis=1)
        if(single_run_table.shape[0] != 0):
            pd.DataFrame.to_csv(single_run_table, output_filepath, index = False)


def main(args):
    # Set user variables
    input_filepath = args.input_filepath
    output_dir = args.output_dir
    
    # Startup messages
    logger.info("Running " + os.path.basename(sys.argv[0]))
    logger.info("Version: " + SCRIPT_VERSION)
    logger.info("Input filepath: " + input_filepath)
    logger.info("Output directory: " + output_dir)

    # Load manifest file
    # TODO - check for second row specifying types and add as a second header row if it exists
    logger.info("Loading manifest file")
    manifest_table = pd.read_csv(input_filepath, header = 0)

    # Does run_ID exist?
    if 'run_ID' not in manifest_table.columns.values.tolist():
        logger.error("Did not find the 'run_ID' column in the provided manifest file. Cannot divide the manifest file by run. Exiting...")
        sys.exit(1)


    # Get unique run IDs
    unique_run_IDs = set(manifest_table['run_ID'])

    # Split table and write
    for run_ID in unique_run_IDs:
        output_filename = "manifest_" + str(run_ID) + ".csv"
        output_filepath = os.path.join(output_dir, output_filename)
        # TODO - check if output_filepath already exists and do not write output unless --force is specified
        logger.info("Writing run '" + str(run_ID) + "' to file '" + output_filename + "'")
        
        single_run_table = manifest_table[manifest_table['run_ID'] == run_ID]
        # Drop run_ID column
        single_run_table = single_run_table.drop(['run_ID'], axis=1)
        if(single_run_table.shape[0] != 0):
            pd.DataFrame.to_csv(single_run_table, output_filepath, index = False)
    
    logger.info(os.path.basename(sys.argv[0]) + ": done.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Simple script to split a QIIME2 manifest file into multiple files based on the run_ID column. "
                                                   "Copyright Jackson M. Tsuji, Neufeld Research Group, 2019. "
                                                   "Version: " + SCRIPT_VERSION)
    parser.add_argument('-i', '--input_filepath', metavar = 'input', required = True,
                       help = 'The path to the input manifest file. Must match QIIME standards AND have a column named "run_ID" with a unique ID for each Illumina run')
    parser.add_argument('-o', '--output_dir', metavar = 'output', required = True,
                       help = 'The directory where output files (named "manifest_[RUN_ID].tsv") will be saved. Will OVERWRITE existing files.')
    
    command_line_args = parser.parse_args()
    main(command_line_args)
