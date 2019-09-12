#!/usr/bin/env python
# generate_combined_ASV_table.py
# Copyright Jackson M. Tsuji, Neufeld Research Group, 2019
# Creates an ASV table with overlaid taxonomy and sequence information for convenience of viewing

# Imports
import sys
import os
import time
import logging
import argparse

from Bio.SeqIO.FastaIO import SimpleFastaParser
import pandas as pd

# Set up the logger
logging.basicConfig(level=logging.INFO, format="[ %(asctime)s UTC ]: %(levelname)s: %(module)s: %(message)s")
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

def main(args):
    # Set user variables
    feature_table_filepath = args.feature_table
    rep_seq_filepath = args.rep_seqs
    taxonomy_filepath = args.taxonomy
    output_filepath = args.output_feature_table

    # Startup messages
    logger.info("Running " + os.path.basename(sys.argv[0]))
    logger.info("Feature table filepath: " + feature_table_filepath)
    logger.info("Representative sequences filepath: " + rep_seq_filepath)
    logger.info("Taxonomy filepath: " + taxonomy_filepath)

    # Load the feature table
    logger.info("Loading feature table")
    feature_table = pd.read_csv(feature_table_filepath, sep = '\t', skiprows = 1, header = 0)
    feature_table = feature_table.rename(columns = {'#OTU ID': 'Feature ID'})

    # Load the FastA file as a pandas dataframe
    # Based on https://stackoverflow.com/a/19452991 (accessed Sept. 12, 2019)
    logger.info("Loading representative sequences FastA file")
    with open(rep_seq_filepath, 'r') as fasta_data:
        fasta_ids = []
        fasta_seqs = []

        for id, seq in SimpleFastaParser(fasta_data):
            fasta_ids.append(id)
            fasta_seqs.append(seq)

    rep_seq_dict = {'Feature ID': fasta_ids, 'ReprSequence': fasta_seqs}
    rep_seq_table = pd.DataFrame(rep_seq_dict)

    # Load taxonomy file
    logger.info("Loading taxonomy file")
    taxonomy_table = pd.read_csv(taxonomy_filepath, sep = '\t', header = 0)
    taxonomy_table = taxonomy_table.rename(columns = {'Taxon': 'Consensus.Lineage'})
    taxonomy_table = taxonomy_table[['Feature ID', 'Consensus.Lineage']]

    # Join
    logger.info("Merging tables")
    merged_table = pd.merge(feature_table, taxonomy_table, how = 'left', on = 'Feature ID', sort = False, validate = 'one_to_one')
    merged_table = pd.merge(merged_table, rep_seq_table, how = 'left', on = 'Feature ID', sort = False, validate = 'one_to_one')

    # Sum columns
    logger.info("Writing merged table to " + output_filepath)
    pd.DataFrame.to_csv(merged_table, output_filepath, sep = '\t', index = False)

    logger.info(os.path.basename(sys.argv[0]) + ": done.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Creates an ASV table with overlaid taxonomy and sequence information for convenience of viewing. "
                                                   "Copyright Jackson M. Tsuji, Neufeld Research Group, 2019.")
    parser.add_argument('-f', '--feature_table', metavar = 'table', required = True, 
                       help = 'The path to the input TSV feature table file.')
    parser.add_argument('-s', '--rep_seqs', metavar = 'seqs', required = True, 
                       help = 'The path to the input FastA representative sequences file.')
    parser.add_argument('-t', '--taxonomy', metavar = 'taxonomy', required = True, 
                       help = 'The path to the input taxonomy file.')
    parser.add_argument('-o', '--output_feature_table', metavar = 'output', required = True, 
                       help = 'The path to the output merged feature table.')
    
    command_line_args = parser.parse_args()
    main(command_line_args)

