from argparse import ArgumentParser
import sys

def args_parse():
    """
    Parse command line arguments into Python
    """
    parser = ArgumentParser(description = "Wrapper to run 16S luigi pipeline")

    parser.add_argument('--manifest', help="""
            Path to Manifest file (.txt) to be imported to qiime
            """,
            required=True)
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
            default="""
                /Data/reference_databases/qiime2/training_classifier/silva132_V4V5_qiime2-2019.7/classifier_silva_132_V4V5.qza
            """
            )

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
                            .replace("<CLASSIFIER_PATH>", args.classifier, 1)

    return config_data

if __name__ == "__main__":
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    template_content = read_template_config()
    config_content = get_luigi_config(template_content, args)

    # Write a config file
    config_path = "configuration/luigi.cfg"
    with open(config_path, 'w') as fh:
        fh.write(config_content)
