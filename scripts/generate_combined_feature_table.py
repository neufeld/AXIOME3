#!/usr/bin/env python
# generate_combined_ASV_table.py
# Copyright Jackson M. Tsuji, Neufeld Research Group, 2019
# Creates a TSV-format QIIME2 feature table with overlaid taxonomy and sequence information for convenience of viewing

# Imports
import sys
import os
import time
import logging
import argparse
import math

from Bio.SeqIO.FastaIO import SimpleFastaParser
import pandas as pd

# Set up the logger
logging.basicConfig(level=logging.INFO, format='[ %(asctime)s UTC ]: %(levelname)s: %(module)s: %(message)s')
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

def read_feature_table(feature_table_filepath):
    """
    Read a QIIME2 feature table

    :param feature_table_filepath: Path to the QIIME2 FeatureTable file, TSV format
    :return: QIIME2 FeatureTable[Frequency] artifact (pandas DataFrame)
    """
    # Load the table
    feature_table = pd.read_csv(feature_table_filepath, sep = '\t', skiprows = 1, header = 0)
    
    # Check if the first column looks okay
    if feature_table.columns.values.tolist()[0] != 'Feature ID':
        if 'Feature ID' in feature_table.columns.values.tolist():
            logger.error('"Feature ID" column already exists in provided feature table and is not the first column. '
                         'Cannot continue. Exiting...')
            sys.exit(1)
        if feature_table.columns.values.tolist()[0] == '#OTU ID':
            logger.debug('Renaming first column of feature table ("#OTU ID") to "Feature ID"')
            feature_table = feature_table.rename(columns = {'#OTU ID': 'Feature ID'})
        else:
            logger.error('Do not recognize the first column of the feature table as feature IDs. Exiting...')
            sys.exit(1)
            
    return(feature_table)

def add_taxonomy_to_feature_table(feature_table, taxonomy_filepath):
    """
    Adds taxonomy values as the Consensus.Lineage column to a QIIME2 feature table

    :param feature_table: QIIME2 FeatureTable[Frequency] artifact loaded as a pandas DataFrame
    :param taxonomy_filepath: Path to the taxonomy.tsv file output by the QIIME2 classifier
    :return: QIIME2 FeatureTable[Frequency] artifact with taxonomy in the Consensus.Lineage column
    """
    # Check if Consensus.Lineage column already exists
    if 'Consensus.Lineage' in feature_table.columns.values.tolist():
        logger.error('"Consensus.Lineage" column already exists in provided feature table. Cannot add taxonomy. Exiting...')
        sys.exit(1)

    # Load taxonomy file
    logger.info('Loading taxonomy file')
    taxonomy_table = pd.read_csv(taxonomy_filepath, sep = '\t', header = 0)
    taxonomy_table = taxonomy_table.rename(columns = {'Taxon': 'Consensus.Lineage'})
    taxonomy_table = taxonomy_table[['Feature ID', 'Consensus.Lineage']]
    
    # Merge
    logger.debug('Adding taxonomy')
    feature_table = pd.merge(feature_table, taxonomy_table, how = 'left', on = 'Feature ID', sort = False, validate = 'one_to_one')
    
    return(feature_table)

def add_rep_seqs_to_feature_table(feature_table, rep_seq_filepath):
    """
    Adds representative sequences as the ReprSequences column to a QIIME2 feature table

    :param feature_table: QIIME2 FeatureTable[Frequency] artifact loaded as a pandas DataFrame
    :param rep_seq_filepath: Path to the dna-sequences.fasta file output by the QIIME2 denoising/clustering step
    :return: QIIME2 FeatureTable[Frequency] artifact with representative sequences in the ReprSequences column
    """
    # Check if ReprSequence column already exists
    if 'ReprSequence' in feature_table.columns.values.tolist():
        logger.error('"ReprSequence" column already exists in provided feature table. '
                    'Cannot add representative sequences. Exiting...')
        sys.exit(1)

    # Load the FastA file as a pandas dataframe
    # Based on https://stackoverflow.com/a/19452991 (accessed Sept. 12, 2019)
    logger.info('Loading representative sequences FastA file')
    with open(rep_seq_filepath, 'r') as fasta_data:
        fasta_ids = []
        fasta_seqs = []

        for id, seq in SimpleFastaParser(fasta_data):
            fasta_ids.append(id)
            fasta_seqs.append(seq)

    rep_seq_dict = {'Feature ID': fasta_ids, 'ReprSequence': fasta_seqs}
    rep_seq_table = pd.DataFrame(rep_seq_dict)
    
    # Merge
    logger.debug('Adding representative sequences')
    feature_table = pd.merge(feature_table, rep_seq_table, how = 'left', on = 'Feature ID', sort = False, validate = 'one_to_one')
    
    return(feature_table)

def sort_feature_table(feature_table):
    """
    Roughly sorts a QIIME2 feature table by percent abundances of Features

    :param feature_table: QIIME2 FeatureTable[Frequency] artifact loaded as a pandas DataFrame
    :return: sorted QIIME2 FeatureTable[Frequency] artifact
    """
    # Sum rows
    # TODO - this still works even if non-sample columns like Consensus.Lineage are there. It ignores non-numeric columns silently.
    # However, longer-term =, a better method to distinguish samples from metadata should be developed.
    features_sum = pd.DataFrame({'Feature ID': feature_table['Feature ID'],
                                'sum': feature_table.iloc[0: ,1:].sum(axis = 1)})
                                
    # Sort
    features_sum = features_sum.sort_values(by = ['sum'], ascending = False)
    
    # The left join seems to automatically handle sorting by the left table
    logger.info('Sorting feature table')
    feature_table = pd.merge(features_sum.drop(columns = 'sum'), feature_table, how = 'left', on = 'Feature ID')
    
    return(feature_table)

def main(args):
    # Set user variables
    feature_table_filepath = args.feature_table
    rep_seq_filepath = args.rep_seqs
    taxonomy_filepath = args.taxonomy
    output_filepath = args.output_feature_table
    feature_id_colname = args.feature_id_colname
    sort_features = args.sort_features
    rename_features = args.rename_features

    # Set sort_features to True if rename_features is True
    if rename_features is True:
        sort_features = True

    # Startup messages
    logger.info('Running ' + os.path.basename(sys.argv[0]))
    logger.info('Feature table filepath: ' + feature_table_filepath)
    logger.info('Representative sequences filepath: ' + str(rep_seq_filepath))
    logger.info('Taxonomy filepath: ' + str(taxonomy_filepath))
    logger.info('Feature ID colname: ' + str(feature_id_colname))
    logger.info('Sort Feature IDs roughly by relative abundance?: ' + str(sort_features))
    logger.info('Rename Feature IDs sequentially?: ' + str(rename_features))

    # Load the feature table
    logger.info('Loading feature table')
    feature_table = read_feature_table(feature_table_filepath)
    
    # Add taxonomy
    if taxonomy_filepath is not False:
        feature_table = add_taxonomy_to_feature_table(feature_table, taxonomy_filepath)

    # Add representative sequences
    if rep_seq_filepath is not False:
        feature_table = add_rep_seqs_to_feature_table(feature_table, rep_seq_filepath)

    # Sort Feature IDs
    if sort_features is True:
        feature_table = sort_feature_table(feature_table)

    # Rename Feature IDs
    if rename_features is True:
        logger.info('Renamng feature IDs sequentially')
        num_rows = feature_table.shape[0]
        feature_table['Feature ID'] = range(num_rows)

    # Change first column to that desired by user
    if feature_id_colname != 'Feature ID':
        logger.info('Changing "Feature ID" colname to "' + feature_id_colname + '"')
        feature_table = feature_table.rename(columns = {'Feature ID': feature_id_colname})

    # Write output
    logger.info('Writing merged table to ' + output_filepath)
    pd.DataFrame.to_csv(feature_table, output_filepath, sep = '\t', index = False)

    logger.info(os.path.basename(sys.argv[0]) + ': done.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Creates a TSV-format QIIME2 feature table with overlaid taxonomy and sequence '
                                                   'information for convenience of viewing. '
                                                   'Copyright Jackson M. Tsuji, Neufeld Research Group, 2019.')
    parser.add_argument('-f', '--feature_table', required = True, 
                       help = 'The path to the input TSV feature table file.')
    parser.add_argument('-s', '--rep_seqs', required = False, default = False, 
                       help = 'The path to the input FastA representative sequences file. Sequences will be added as the '
                       '"ReprSequences" column. You can optionally omit this flag and not have sequences added to the table.')
    parser.add_argument('-t', '--taxonomy', required = False, default = False, 
                       help = 'The path to the input taxonomy file. Taxonomy will be added as the "Consensus.Lineage" column. '
                       'You can optionally omit this flag and not have taxonomy added to the table.')
    parser.add_argument('-o', '--output_feature_table', required = True, 
                       help = 'The path to the output TSV feature table.')
    parser.add_argument('-N', '--feature_id_colname', required = False, default = 'Feature ID', 
                       help = 'The name of the first column of the output ASV table. [Default: "Feature ID"]')
    parser.add_argument('-S', '--sort_features', required = False, action = 'store_true', 
                       help = 'Optionally sort Feature IDs roughly based on overall abundance.')
    parser.add_argument('-R', '--rename_features', required = False, action = 'store_true', 
                       help = 'Optionally rename the Feature IDs sequentially, roughly based on overall abundance. '
                       'Automatically sets --sort_features')
    
    command_line_args = parser.parse_args()
    main(command_line_args)
