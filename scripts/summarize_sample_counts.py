#!/usr/bin/env python
# summarize_sample_counts.py
# Copyright Jackson M. Tsuji, Neufeld Research Group, 2019
# Creates a tabular summary of the total read counts of all samples in a qiime2 feature table

# Imports
import sys
import os
import time
import logging
import argparse
import uuid
import biom

import zipfile as zf
import pandas as pd

# GLOBAL variables
SCRIPT_VERSION = '0.8.0'
BIOM_PATH_PARTIAL = 'data/feature-table.biom' # biom file location within the unzipped QZA file

# Set up the logger
logging.basicConfig(level=logging.INFO, format="[ %(asctime)s UTC ]: %(levelname)s: %(module)s: %(message)s")
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

def main(args):
    # Set user variables
    input_filepath = args.input_filepath
    output_filepath = args.output_filepath
    min_count_filepath = args.min_count_filepath

    # Startup messages
    logger.info("Running " + os.path.basename(sys.argv[0]))
    logger.info("Version: " + SCRIPT_VERSION)
    logger.info("Input filepath: " + input_filepath)
    logger.info("Output directory: " + output_filepath)
    logger.info("Min count filepath: " + str(min_count_filepath))

    # Load the BIOM table from within the QZA (ZIP) file
    logger.info("Loading QZA file")
    with zf.ZipFile(input_filepath, mode = 'r') as qza_data:
        # Dump list of contents and determine path to the BIOM file
        qza_data_contents = qza_data.namelist()

        # Find the path to the biom file
        # See https://stackoverflow.com/a/12845341 (accessed Sept. 12, 2019)
        biom_filepath = list(filter(lambda x: BIOM_PATH_PARTIAL in x, qza_data_contents))
        # TODO - check this is a list of length 1
        logger.debug("Found biom file in QZA file at " + str(biom_filepath[0]))
        
        # Extract the biom file to /tmp
        tmpdir = os.path.join('/tmp', uuid.uuid4().hex)
        extraction_path = qza_data.extract(biom_filepath[0], path = tmpdir)
        logger.debug("Extracted temp BIOM file to " + extraction_path)

    # Load biom file and convert to pandas dataframe
    logger.info("Loading BIOM file")
    biom_data = biom.load_table(extraction_path)
    biom_table = biom_data.to_dataframe()

    # Delete tmp file
    logger.debug("Removing tmp file " + extraction_path)
    os.remove(extraction_path)
    logger.debug("Removing tmp dir " + os.path.dirname(extraction_path))
    os.rmdir(os.path.dirname(extraction_path))

    # Sum columns
    logger.info("Summarizing BIOM file")
    sample_counts = biom_table.sum().to_frame(name = "count")
    # Move sample IDs to their own column (not row IDs)    
    # See https://stackoverflow.com/a/25457946 (accessed Sept. 12, 2019)
    sample_counts.index.name = 'sample-id'
    sample_counts = sample_counts.reset_index()
    # Sort by count
    sample_counts = sample_counts.sort_values(by = sample_counts.columns[1])

    # Write output
    logger.info("Writing counts summary file to " + output_filepath)
    pd.DataFrame.to_csv(sample_counts, output_filepath, sep = '\t', index = False)

    # Get min count and write, if desired
    if min_count_filepath is not False:
        logger.info("Writing min count to " + min_count_filepath)
        min_count = int(sample_counts.iat[0,1])
        with open(min_count_filepath, 'w') as min_count_file:
            min_count_file.write(str(min_count) + '\n')

    logger.info(os.path.basename(sys.argv[0]) + ": done.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Creates a tabular summary of the total read counts of all samples in a qiime2 feature table. "
                                                   "Copyright Jackson M. Tsuji, Neufeld Research Group, 2019. "
                                                   "Version: " + SCRIPT_VERSION)
    parser.add_argument('-i', '--input_filepath', metavar = 'input', required = True, 
                       help = 'The path to the input QZA FeatureTable file.')
    parser.add_argument('-o', '--output_filepath', metavar = 'output', required = True, 
                       help = 'The path to the output TSV file.')
    parser.add_argument('-m', '--min_count_filepath', metavar = 'output', required = False, default = False, 
                       help = 'Optional path to write a single-line text file with the lowest count value in the dataset.')
    
    command_line_args = parser.parse_args()
    main(command_line_args)

