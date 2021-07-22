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
import re

from scripts.qiime2_helper.fasta_parser import get_id_and_seq
import pandas as pd
import qiime2
from qiime2 import Artifact

# GLOBAL VARIABLES
SCRIPT_VERSION = '0.8.1'

# Set up the logger
logging.basicConfig(format='[ %(asctime)s UTC ]: %(levelname)s: %(message)s')
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)

def import_qiime2_feature_table(feature_table_filepath):
    """
    Convert QIIME2 feature table artifact to compatible format
    """
    artifact = Artifact.load(feature_table_filepath)
    artifact_type = str(artifact.type)

    if(artifact_type == "FeatureTable[Frequency]" or
        artifact_type == "FeatureTable[RelativeFrequency]"):

        feature_table_df = artifact.view(pd.DataFrame)

        # return transposed version for better view
        transposed = feature_table_df.T
        transposed.index.name = "SampleID"

        return transposed.reset_index()
    # raise error if not feature table artifact
    else:
        raise ValueError("Input artifact is not of type FeatureTable[Frequency] or FeatureTable[RelativeFrequency]!")

def import_qiime2_taxonomy(taxonomy_filepath):
    """
    Convert QIIME2 taxonomy artifact to compatible format
    """
    artifact = Artifact.load(taxonomy_filepath)
    artifact_type = str(artifact.type)
    
    if(artifact_type == "FeatureData[Taxonomy]"):
        taxonomy_df = artifact.view(pd.DataFrame)

        return taxonomy_df.reset_index()
    # raise error if not feature table artifact
    else:
        raise ValueError("Input artifact is not of type FeatureData[Taxonomy]!")

def read_feature_table(feature_table_filepath):
    """
    Read a QIIME2 feature table

    :param feature_table_filepath: Path to the QIIME2 FeatureTable file, TSV format
    :return: QIIME2 FeatureTable[Frequency] artifact (pandas DataFrame)
    """
    # Load the table
    #feature_table = pd.read_csv(feature_table_filepath, sep = '\t')
    feature_table = import_qiime2_feature_table(feature_table_filepath)
    # QIIME2 compatible ID column names
    allowed_ids = qiime2.metadata.metadata.FORMATTED_ID_HEADERS
    # First column in the feature_table df
    first_col = list(feature_table.columns)[0]
    
    # Check if the first column looks okay
    if first_col != 'Feature ID':
        if 'Feature ID' in feature_table.columns:
            logger.error('"Feature ID" column already exists in provided feature table and is not the first column. '
                         'Cannot continue. Exiting...')
            sys.exit(1)
        if first_col in allowed_ids:
            logger.debug('Renaming first column of feature table ("{col}") to "Feature ID"'.format(col=first_col))
            feature_table = feature_table.rename(columns = {first_col: 'Feature ID'})
        elif first_col.lower() in allowed_ids:
            logger.debug('Renaming first column of feature table ("{col}") to "Feature ID"'.format(col=first_col))
            feature_table = feature_table.rename(columns = {first_col: 'Feature ID'})
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
    taxonomy_table = import_qiime2_taxonomy(taxonomy_filepath)
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

    fasta_ids = []
    fasta_seqs = []
    for _id, seq in get_id_and_seq(rep_seq_filepath):
        fasta_ids.append(_id)
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

def parse_silva_taxonomy_entry(taxonomy_entry, resolve = True):
    """
    Parse a single Silva taxonomy entry

    :param taxonomy_entry: Silva taxonomy string (see example below)
    :return: list of 7 rank entries for the taxonomy
    """
    # Example:
    # D_0__Bacteria;D_1__Margulisbacteria;D_2__microbial mat metagenome;D_3__microbial mat metagenome;D_4__microbial mat metagenome;D_5__microbial mat metagenome;D_6__microbial mat metagenome

    taxonomy_split = str(taxonomy_entry).split(sep=';')

    if len(taxonomy_split) > 7:
        logger.error('Taxonomy entry is ' + str(len(taxonomy_split)) + ' long, not 7 as expected. Exiting...')
        logger.error('Entry was: "' + taxonomy_entry + '"')
        sys.exit(1)
    elif len(taxonomy_split) < 7:
        # Sometimes Silva entries are short; rest is unresolved
        for entry_index in range(len(taxonomy_split)+1, 8):
            taxonomy_split.append('')

    # Remove header pieces
    # TODO - confirm they are in the right order (0,1,2,3,4,5,6)
    taxonomy_split = [re.sub("D_[0-6]__", "", level) for level in taxonomy_split]

    # Fill in empty parts, if they exist
    if '' in taxonomy_split and resolve is True:
        # Get the positions of the empty spots
        empty_taxa = []
        for taxonomy_level in taxonomy_split:
            if taxonomy_level == '':
                empty_taxa.append(True)
            else:
                empty_taxa.append(False)

        # Get the numeric index of the first empty taxon
        # See https://stackoverflow.com/a/9542768, accessed Sept. 18, 2019
        first_empty_taxon = empty_taxa.index(True)

        if False in empty_taxa[first_empty_taxon:]:
            logger.error(
                'There seems to be an empty entry in the middle of your taxonomy levels. Cannot resolve. Exiting...')
            logger.error('Entry was: ' + ', '.join(taxonomy_entry))
            sys.exit(1)

        filler_entry = 'Unresolved_' + taxonomy_split[(first_empty_taxon - 1)]

        for taxonomy_level_index in range(first_empty_taxon, 7):
            taxonomy_split[taxonomy_level_index] = filler_entry

    return (taxonomy_split)

def add_row_id(feature_table):
    """
    Add numerical row ID to feature table as the first column
    """
    num_rows = feature_table.shape[0]
    row_id_col = [i for i in range(0, num_rows)]

    # Insert id column in the beginning
    feature_table.insert(0, column="rowID", value=row_id_col)

    return feature_table

def combine_table(feature_table_filepath, rep_seq_filepath, taxonomy_filepath,
        output_filepath):
    """
    Generates combined feature table.

    Input:
        - feature_table_filepath: feature table file (.tsv)
        - rep_seq_filepath: representative sequence file (.fasta)
        - taxonomy_filepath: taxonomy classification file (.tsv)
        - output_filepath: Path to save output
    """

    feature_table = read_feature_table(feature_table_filepath)

    # Add taxonomy information
    feature_table = add_taxonomy_to_feature_table(
            feature_table,
            taxonomy_filepath
    )
    # Add row IDs as column in the beginning
    feature_table = add_row_id(feature_table)

    # Add representative sequences
    feature_table = add_rep_seqs_to_feature_table(
            feature_table,
            rep_seq_filepath
    )

    # Save output
    feature_table.to_csv(output_filepath, sep = '\t', index
                                = False)

def main(args):
    # Set user variables
    feature_table_filepath = args.feature_table
    rep_seq_filepath = args.rep_seqs
    taxonomy_filepath = args.taxonomy
    output_filepath = args.output_feature_table
    feature_id_colname = args.feature_id_colname
    sort_features = args.sort_features
    rename_features = args.rename_features
    parse_taxonomy = args.parse_taxonomy
    verbose = args.verbose

    # Set logger verbosity
    if verbose is True:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Set sort_features to True if rename_features is True
    if rename_features is True:
        sort_features = True

    # Check that taxonomy_filepath is set if parse_taxonomy is True
    if (parse_taxonomy is True) and (taxonomy_filepath is False):
        logger.error('Specified --parse_taxonomy but did not specify --taxonomy_filepath. Exiting...')
        sys.exit(1)

    # Startup messages
    logger.info('Running ' + os.path.basename(sys.argv[0]))
    logger.info('Version: ' + SCRIPT_VERSION)
    logger.info('### SETTINGS ###')
    logger.info('Feature table filepath: ' + feature_table_filepath)
    logger.info('Representative sequences filepath: ' + str(rep_seq_filepath))
    logger.info('Taxonomy filepath: ' + str(taxonomy_filepath))
    logger.info('Feature ID colname: ' + str(feature_id_colname))
    logger.info('Sort Feature IDs roughly by relative abundance?: ' + str(sort_features))
    logger.info('Rename Feature IDs sequentially?: ' + str(rename_features))
    logger.info('Parse Silva taxonomy into 7 ranks?: ' + str(parse_taxonomy))
    logger.info('Verbose logging: ' + str(verbose))
    logger.info('################')

    # Load the feature table
    logger.info('Loading feature table')
    feature_table = read_feature_table(feature_table_filepath)
    
    # Add taxonomy
    if taxonomy_filepath is not False:
        feature_table = add_taxonomy_to_feature_table(feature_table, taxonomy_filepath)

    # Parse taxonomy
    if parse_taxonomy is True:
        logger.info('Parsing taxonomy into 7 ranks')

        # TODO - expose 'resolve' option to user
        taxonomy_entries_parsed = map(lambda entry: parse_silva_taxonomy_entry(entry, resolve=True),
                                      feature_table['Consensus.Lineage'].tolist())
        taxonomy_table_parsed = pd.DataFrame(taxonomy_entries_parsed,
                                             columns=['Domain', 'Phylum', 'Class', 'Order', 'Family', 'Genus',
                                                      'Species'])

        # Bind to main table in place of 'Consensus.Lineage'
        feature_table = pd.concat([feature_table, taxonomy_table_parsed], axis=1, sort=False)
        feature_table = feature_table.drop(columns='Consensus.Lineage')

    # Add row IDs as column in the beginning
    feature_table = add_row_id(feature_table)

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
    if output_filepath == '-':
        # Write to STDOUT
        logger.info("Writing merged table to STDOUT")
        feature_table.to_csv(sys.stdout, sep = '\t', index = False)
    else:
        logger.info('Writing merged table to ' + output_filepath)
        feature_table.to_csv(output_filepath, sep = '\t', index = False)

    logger.info(os.path.basename(sys.argv[0]) + ': done.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Creates a TSV-format QIIME2 feature table with overlaid taxonomy and sequence '
                                                   'information for convenience of viewing. '
                                                   'Copyright Jackson M. Tsuji, Neufeld Research Group, 2019. '
                                                   'Version: ' + SCRIPT_VERSION)
    parser.add_argument('-f', '--feature_table', required = True, 
                       help = 'The path to the input TSV feature table file.')
    parser.add_argument('-s', '--rep_seqs', required = False, default = False, 
                       help = 'The path to the input FastA representative sequences file. Sequences will be added as the '
                       '"ReprSequences" column. You can optionally omit this flag and not have sequences added to the table.')
    parser.add_argument('-t', '--taxonomy', required = False, default = False, 
                       help = 'The path to the input taxonomy file. Taxonomy will be added as the "Consensus.Lineage" column. '
                       'You can optionally omit this flag and not have taxonomy added to the table.')
    parser.add_argument('-o', '--output_feature_table', required = False, default = '-',
                       help = 'The path to the output TSV feature table. Will write to STDOUT (-) if nothing is provided.')
    parser.add_argument('-N', '--feature_id_colname', required = False, default = 'Feature ID', 
                       help = 'The name of the first column of the output ASV table. [Default: "Feature ID"]')
    parser.add_argument('-S', '--sort_features', required = False, action = 'store_true', 
                       help = 'Optionally sort Feature IDs roughly based on overall abundance.')
    parser.add_argument('-R', '--rename_features', required = False, action = 'store_true', 
                       help = 'Optionally rename the Feature IDs sequentially, roughly based on overall abundance. '
                       'Automatically sets --sort_features')
    parser.add_argument('-P', '--parse_taxonomy', required=False, action='store_true',
                        help= 'Optionally parse Silva taxonomy into 7 ranks with columns "domain", "phylum", etc.')
    parser.add_argument('-v', '--verbose', required=False, action='store_true',
                       help = 'Enable for verbose logging.')
    # TODO - add option to auto-detect if a QZA file is provided instead of the unpackaged file. Deal with the converstions. Same for if a BIOM file is provided.
    
    command_line_args = parser.parse_args()
    main(command_line_args)
