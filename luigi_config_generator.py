"""
This is a temporary script to generate configuration file for luigi framewoork.
It will be deprecated in the future development. 
"""
from argparse import ArgumentParser
import sys
import subprocess
import os

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def args_parse():
    """
    Parse command line arguments into Python
    """
    parser = ArgumentParser(description = "Wrapper to run 16S luigi pipeline")

    parser.add_argument('--manifest', help="""
            Path to Manifest file (.txt) to be imported to qiime
            """,
            required=True)

    parser.add_argument('--metadata', help="""
            Path to Metadata file (.txt) to be imported to qiime
            """)

    parser.add_argument('--sample-type', help="""
            The semantic type of the artifact that will be created upon
            importing.
            [ default = SampleData[PairedEndSequencesWithQuality] ]
            """,
            default="SampleData[PairedEndSequencesWithQuality]")

    parser.add_argument('--input-format', help="""
            The format of the data to be imported.
            [ default = PairedEndFastqManifestPhred33 ]
            """,
            default="PairedEndFastqManifestPhred33")

    parser.add_argument('--trim-left-f', help="""
            Corresponds to --p-trim-left-f in Dada2. Number of bases to trim
            from the 5` end in the forward read. [ default = 19 ]
            """,
            default=19)

    parser.add_argument('--trunc-len-f', help="""
            Corresponds to --p-trunc-len-f in Dada2. Truncates 3` end in the
            forward read.
            """,
            default=250)

    parser.add_argument('--trim-left-r', help="""
            Corresponds to --p-trim-left-r in Dada2. Number of bases to trim
            from the 5` end in the reverse read. [ default = 19 ]
            """,
            default=20)

    parser.add_argument('--trunc-len-r', help="""
            Corresponds to --p-trunc-len-f in Dada2. Truncates the 3` end in the
            reverse read.
            """,
            default=250)

    parser.add_argument('--classifier', help="""
            Path to the classifier file. Make sure to use the classifier that
            matches your qiime2 version. (It will fail if the version
            mismatches) [ default = qiime2-2019-07 version ]
            """,
            default="/Data/reference_databases/qiime2/training_classifier/silva132_V4V5_qiime2-2019.7/classifier_silva_132_V4V5.qza"
            )

    parser.add_argument('--sampling-depth', help="""
            The total frequency that each sample should be rarefied to.
            """,
            default=10000)

    parser.add_argument('--abundance-threshold', help="""
            % abundance threshold to filter ASV table by (0 to 1). 0 means no
            filtering done. [Default = 0.05]
            """,
            default=0.05)

    parser.add_argument('--r2-threshold', help="""
            (For triplot). Only display environmental metadata if R2 value is
            greather than the threshold. [Default = 0.3]
            """,
            default=0.3)

    return parser

def read_template_config():
    """
    Read template configuration file, and store it as a string
    Assumes template.cfg is in "configuration" directory
    """

    template = "configuration/template.cfg"

    with open(template, 'r') as fh:
        file_content = fh.readlines()

    return ''.join(file_content)

def get_luigi_config(template, args):
    """
    Read template config file line by line, and replace fields with user inputs
    """

    config_data = template.replace("<MANIFEST_PATH>", args.manifest, 1)\
                    .replace("<SAMPLE_TYPE>", args.sample_type, 1)\
                    .replace("<INPUT_FORMAT>", args.input_format, 1)\
                    .replace("<TRIM_LEFT_F>", str(args.trim_left_f), 1)\
                    .replace("<TRUNC_LEN_F>", str(args.trunc_len_f), 1)\
                    .replace("<TRIM_LEFT_R>", str(args.trim_left_r), 1)\
                    .replace("<TRUNC_LEN_R>", str(args.trunc_len_r), 1)\
                    .replace("<CLASSIFIER_PATH>", args.classifier, 1)\
                    .replace("<SAMPLING_DEPTH>", str(args.sampling_depth), 1)\
                    .replace("<ABUNDANCE_THRESHOLD>", str(args.abundance_threshold))\
                    .replace("<R2_THRESHOLD>", str(args.r2_threshold))

    # Check if metadata file is provided
    if(args.metadata):
        config_data = config_data.replace("<METADATA_PATH>", args.metadata, 1)\
    # Check if multiple_run column exists in manifest file
    # For now, assume first line is header?
    with open(args.manifest, 'r') as fh:
        header = fh.readline()
        if("run_ID" in header):
            config_data = config_data.replace("<IS_MULTIPLE>", "y", 1)

    return config_data

def check_env():
    reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
    installed_packages = [r.decode().split('==')[0] for r in reqs.split()]

    # Color formatter
    formatters = {
            'RED': '\033[91m',
            'GREEN': '\033[92m',
            'END': '\033[0m'
            }

    # check if required packges exist
    # check if luigi exists
    isGood = True

    if not('luigi' in installed_packages):
        msg = "\nluigi is not installed!!\n" +\
        "Please install luigi by following the instruction below\n\n" +\
        "> Activate your qiime2 conda environment if you haven't done yet\n" +\
        "{RED}conda activate YOUR_QIIME2_ENVIRONMENT{END}\n".format(**formatters) +\
        "> Check pip is pointing to your anaconda packages\n" +\
        "{RED}which pip{END}\n".format(**formatters) +\
        "> Should print something like " +\
        "{GREEN}/Winnebago/danielm710/anaconda3/envs/qiime2-2019.7/bin/pip{END}\n".format(**formatters) +\
        "> Install luigi\n" +\
        "{RED}pip install luigi{END}\n".format(
                **formatters
                )
        print(msg)
        print("-----------------------------------------")
        isGood = False
    if not('biopython' in installed_packages):
        msg = "\nbiopython is not installed!!\n" +\
        "Please install biopython by following the instruction below\n\n" +\
        "> Activate your qiime2 conda environment if you haven't done yet\n" +\
        "{RED}conda activate YOUR_QIIME2_ENVIRONMENT{END}\n".format(**formatters) +\
        "> Install biopython\n" +\
        "{RED}conda install -c bioconda biopython pandas{END}\n".format(
                **formatters
                )
        print(msg)
        isGood = False

    if not(isGood):
        sys.exit(1)

def check_outdir(outdir, is_first):
    if(is_first):
        if(os.path.isdir(outdir)):
            msg = "'output' directory already exists!\n" +\
                    "Please remove/rename/move the existing directory"
            print()
            print(msg)
            print()
            sys.exit(1)
    else:
        if not(os.path.isdir(outdir)):
            msg = "Different output directory specified!\n" +\
                    "Please specify the same value you used in the first " +\
                    "run for --out-prefix"
            print()
            print(msg)
            print()
            sys.exit(1)

if __name__ == "__main__":
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Check if required python packages exist
    check_env()

    # Generate config for luigi to use
    template_content = read_template_config()
    config_content = get_luigi_config(template_content, args)

    # Write a config file
    config_path = "configuration/luigi.cfg"
    with open(config_path, 'w') as fh:
        fh.write(config_content)
