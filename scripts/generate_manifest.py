from argparse import ArgumentParser
import sys
import os
import glob
import re

# Colour formatters
formatters = {
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'REVERSE': '\033[7m',
        'UNDERLINE': '\033[4m',
        'END': '\033[0m'
        }

def args_parse():
    """
    Parse command line arguments into Python
    """
    parser = ArgumentParser(description = "Script to generate manifest file for qiime2")

    parser.add_argument('--samplesheet', help="""
            Path to samplesheet (.csv) used for MiSeq. *Make sure SampleSheet
            ONLY has your samples (if it contains multiple users' samples)*
            """,
            required=True)

    parser.add_argument('--data-dir', help="""
            Directory containing MiSeq data (files should be gunzipped). It
            does not necessarilly have to have just your samples.
            """,
            required=True)

    return parser

def natural_sort_key(string):
    """
    Performs natural sort. First sort by alphabet, then by numeral.
    Assumes line is comma separated, and has same format as qiime 2 manifest
    file. (e.g. sample_name, path, direction)
    """

    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = [ convert(s) for s in re.split('([0-9]+)', string)]

    return alphanum_key

def read_samplesheet(samplesheet_path):
    """
    Read Samplesheet.csv and extract relevant information.
    Assumes Samplesheet has preset header, and no lines are present past [data]
    line.

    Returns a dictionry (Assumes unique Sample_Name)
    {sample_Name: sample_ID}
    """

    # Check if file exists
    if not(os.path.isfile(samplesheet_path)):
        raise FileNotFoundError("Specified samplesheet does NOT exist...\n")

    # Preset header in samplesheet
    # Assume this will always exist in every samplesheet
    header = "Sample_ID,Sample_Name"

    # Start processing when this is set to true
    should_process = False
    # List to store processed data
    processed_data = {}

    with open(samplesheet_path, 'r') as fh:
        for line in fh:
            line = line.strip()
            # Start procesing when header line encountered
            if(header in line):
                should_process = True
                continue

            if(should_process and line):
                info = line.split(",")

                # Skip if blank line (deem as blank line if either ID or name
                # is missing)
                if not(info[0] or info[1]):
                    continue

                sample_id = info[0] # Sample ID
                sample_name = info[1] # Sample Name

                # Check if duplicate key exists
                # System will exit with warning
                if(sample_name in processed_data):
                    print("Duplicate Sample_Name exists in the samplesheet. " +\
                            "Please change the samplesheet, and make sure " +\
                            "data-dir does not have fastq.gz files with " +\
                            "the same name")
                    sys.exit(1)
                processed_data[sample_name] = sample_id

    if(len(processed_data) == 0):
        raise ValueError("Samplesheet has zero samples\n")

    return processed_data

def generate_manifest(samplesheet_processed, data_dir):
    """
    Generate manifest file based on the provided samplesheet, and Illumina
    MiSeq Data

    Arguments
        - samplesheet_processed: dictionary {sample_name: sample_id} as described
        in the samplesheet
        - data_dir: directory containing all the MiSeq samples
        - formatters: color formatters for print

    Return
        - Manifest file content as a string
    """

    # Check data_dir exist
    if not(os.path.isdir(data_dir)):
        raise FileNotFoundError("Specified data_dir does NOT exist...\n")

    manifest_lines = []
    excluded_files = []
    # Remove element whenever it's "processed"
    # Shallow copy is fine since it's not nested dictionary
    excluded_sample_dict = samplesheet_processed.copy()

    for f in os.listdir(data_dir):
        # Fastq files are gunzipped (has a format *.fastq.gz)
        if f.endswith(".fastq.gz"):
            # manifest file content
            direction = ''
            manifest_line = ''

            # Retrieve matching fastq files using samplesheet
            # Sample_Name is first substring separated by "_"
            sample_name = f.split('_')[0]

            # Warn user if data_dir has fastq file not present in the
            # samplesheet
            if not (sample_name in samplesheet_processed):
                excluded_files.append(f)
                continue
            sample_id = samplesheet_processed[sample_name]

            abspath = os.path.abspath(os.path.join(data_dir, f))

            # Case 1: Forward read
            # Has "R1" in the file name
            if("R1" in f):
                direction = "forward"

            # Case 2: Reverse read
            # Has "R2" in the file name
            elif("R2" in f):
                direction = "reverse"

            # Check if direction is not defined
            else:
                "Direction not specified in the file: {_file}".format(
                        _file = f)

            manifest_line = ','.join([sample_id, abspath, direction])
            manifest_lines.append(manifest_line)

            # Remove dictionary key when it's done processing
            excluded_sample_dict.pop(sample_name, None)


    # Print files that are present in the directory, but not in the samplesheet
    if(excluded_files):
        formatted_excluded_files = ''
        colwidth = max(len(f) for f in excluded_files) + 3
        column = 4
        count = 0
        for f in sorted(excluded_files, key=natural_sort_key):
            if(count % column == 0 and count != 0):
                formatted_excluded_files = '\n'.join([formatted_excluded_files, f.ljust(colwidth)])
            else:
                formatted_excluded_files = ''.join([formatted_excluded_files, f.ljust(colwidth)])

            count = count + 1

        warning_msg = "{RED}WARNING!\n{END}".format(**formatters) +\
                "Excluding following files in the manifest file because " +\
                "{UNDERLINE}corresponding Sample_Name could not be found{END}".format(
                        **formatters) +\
                "{UNDERLINE} in the provided SampleSheet.{END}\n\n".format(
                        **formatters) +\
                "{files}\n".format(files=formatted_excluded_files)

        print(warning_msg)

    # Print files that are present in the samplesheet, but not in the directory
    missing_files = []
    if(excluded_sample_dict):
        # Construct file names based on Sample_Name
        for s_name in excluded_sample_dict:
            # Construct file name
            missing_forward = s_name + "_S" + s_name + "_L001_R1_001.fastq.gz"
            missing_reverse = s_name + "_S" + s_name + "_L001_R2_001.fastq.gz"

            missing_files.append(missing_forward)
            missing_files.append(missing_reverse)

        formatted_missing_files = ''
        colwidth = max(len(f) for f in missing_files) + 3
        column = 4
        count = 0
        for f in sorted(missing_files, key=natural_sort_key):
            if(count % column == 0 and count != 0):
                formatted_missing_files = '\n'.join([formatted_missing_files, f.ljust(colwidth)])
            else:
                formatted_missing_files = ''.join([formatted_missing_files, f.ljust(colwidth)])

            count = count + 1

        warning_msg = "{RED}WARNING!\n{END}".format(**formatters) +\
                "Following files are found in the samplesheet, " +\
                "{UNDERLINE}but NOT in the specified --data-dir{END}\n\n".format(
                        **formatters) +\
                "{files}\n".format(files=formatted_missing_files)

        print(warning_msg)

    return manifest_lines, excluded_files, missing_files

if __name__ == "__main__":
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Read Samplesheet.csv
    samplesheet_processed = read_samplesheet(args.samplesheet)

    # Get manifest file content
    manifest_lines, _, _ = generate_manifest(
            samplesheet_processed,
            args.data_dir)

    sorted_manifest = sorted(manifest_lines,
            key=lambda x:
                (natural_sort_key(x.split(',')[0]),
                x.split(',')[2]))

    # Write output
    with open("manifest.txt", 'w') as fh:
        # Write header
        fh.write("sample-id,absolute-filepath,direction\n")
        fh.write('\n'.join(sorted_manifest))

    print("--------------------------------------------------")
    print("Generated manifest.txt in the current directory!\n" +\
            "Full path to the generated manifest file: " +\
            "{REVERSE}{manifest_path}{END}\n".format(
                    manifest_path = os.path.abspath("manifest.txt"),
                    REVERSE=formatters['REVERSE'],
                    END=formatters['END']
                ))
