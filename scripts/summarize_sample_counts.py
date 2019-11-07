#!/usr/bin/env python
# summarize_sample_counts.py
# Copyright Jackson M. Tsuji, Neufeld Research Group, 2019
# Creates a tabular summary of the total read counts of all samples in a qiime2 feature table

# Imports
import sys
import os
import shutil
import time
import logging
import argparse
import uuid
import biom

import zipfile as zf
import pandas as pd

# GLOBAL variables
SCRIPT_VERSION = '0.8.1'
BIOM_PATH_PARTIAL = 'data/feature-table.biom' # biom file location within the unzipped QZA file

# Set up the logger
logging.basicConfig(format="[ %(asctime)s UTC ]: %(levelname)s: %(message)s")
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

def unpack_biom_from_qza(input_filepath, tmp_dir_base):
    """
    Unzip a BIOM file from a QIIME2 QZA archive.

    :global BIOM_PATH_PARTIAL: partial path to the biom file within the QZA archive
    :param input_filepath: Path to the QIIME2 QZA archive, FeatureTable[Frequency] format
    :param tmp_dir_base: The base directory to extract the ZIP file to (will create a random subfolder)
    :return: tuple of the path to the unzipped BIOM file and the path to the random temp subfolder
    """
    logger.info("Unpacking QZA file")
    
    with zf.ZipFile(input_filepath, mode='r') as qza_data:
        # Dump list of contents and determine path to the BIOM file
        qza_data_contents = qza_data.namelist()

        # Find the path to the biom file
        # See https://stackoverflow.com/a/12845341 (accessed Sept. 12, 2019)
        biom_filepath = list(filter(lambda x: BIOM_PATH_PARTIAL in x, qza_data_contents))
        # TODO - check this is a list of length 1
        logger.debug("Found biom file in QZA file at " + str(biom_filepath[0]))
        
        # Extract the biom file to a randomly generated subfolder in tmp_dir_base
        tmpdir = os.path.join(tmp_dir_base, uuid.uuid4().hex)
        logger.debug("Extracting into temp subdir " + tmpdir)
        extraction_path = qza_data.extract(biom_filepath[0], path = tmpdir)
        logger.debug("Extracted temp BIOM file to " + extraction_path)
    
    # Return the path to the BIOM file and to the random subfolder
    biom_tmp_info = (extraction_path, tmpdir)
    return(biom_tmp_info)

def load_biom_df_from_qza(input_filepath, tmp_dir_base):
    """
    Load a BIOM file from a QIIME2 QZA archive as a Pandas dataframe.

    :global BIOM_PATH_PARTIAL: partial path to the biom file within the QZA archive
    :param input_filepath: Path to the QIIME2 QZA archive, FeatureTable[Frequency] format
    :param tmp_dir_base: The base directory to extract the ZIP file to (will create a random subfolder)
    :return: pandas DataFrame of the BIOM table's count data
    """
    # Unzip the BIOM table from within the QZA (ZIP) file
    biom_tmp_info = unpack_biom_from_qza(input_filepath, tmp_dir_base)

    # Load biom file and convert to pandas dataframe
    logger.info("Loading BIOM file")
    biom_data = biom.load_table(biom_tmp_info[0])
    biom_table = biom_data.to_dataframe()

    # Delete tmp dir
    logger.debug("Removing temp dir " + biom_tmp_info[1])
    shutil.rmtree(biom_tmp_info[1])
    
    return(biom_table)

def main(args):
    # Set user variables
    input_filepath = args.input_filepath
    output_filepath = args.output_filepath
    min_count_filepath = args.min_count_filepath
    tmp_dir_base = args.tmp_dir
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
    logger.info("Output filepath: " + output_filepath)
    logger.info("Min count filepath: " + str(min_count_filepath))
    logger.info("Temp directory: " + tmp_dir_base)
    logger.info("Verbose logging: " + str(verbose))

    # Load the BIOM table from within the QZA (ZIP) file
    biom_table = load_biom_df_from_qza(input_filepath, tmp_dir_base)

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
    if output_filepath == '-':
        # Write to STDOUT
        logger.info("Writing counts summary file to STDOUT")
        sample_counts.to_csv(sys.stdout, sep='\t', index=False)
    else:
        logger.info("Writing counts summary file to " + output_filepath)
        sample_counts.to_csv(output_filepath, sep='\t', index=False)

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
    parser.add_argument('-i', '--input_filepath', required=True, 
                       help = 'The path to the input QZA FeatureTable file.')
    parser.add_argument('-o', '--output_filepath', required=False, default='-', 
                       help = 'The path to the output TSV file. Will write to STDOUT (-) if nothing is provided.')
    parser.add_argument('-m', '--min_count_filepath', required=False, default=False, 
                       help = 'Optional path to write a single-line text file with the lowest count value in the dataset.')
    parser.add_argument('-T', '--tmp_dir', required=False, default='/tmp', 
                       help = 'Optional path to the temporary directory used for unpacking the QZA [default: /tmp].')
    parser.add_argument('-v', '--verbose', required=False, action='store_true',
                       help = 'Enable for verbose logging.')
    command_line_args = parser.parse_args()
    
    main(command_line_args)
