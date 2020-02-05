# Custom module
from generate_pcoa import *

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

    parser.add_argument('--pcoa-qza', help="""
            QIIME2 PCoA artifact (.qza)
            """,
            required=True)

    parser.add_argument('--metadata', help="""
            Metadata file used for QIIME2. It will IGNORE commented lines.
            Requires first column to be Sample ID column
            """,
            required=True)

    parser.add_argument('--point-size', help="""
            Geom_point size. Default 6
            """,
            type=int,
            default=6)

    parser.add_argument('--output-dir', help="""
            Path to store output pdf as
            """,
            default='.')

    return parser

def run_multiple(pcoa, metadata_df, point_size):
    """
    Save multiple PCoA plots in a single pdf file
    """

    cols = metadata_df.columns

    for column in cols:
        yield generate_pcoa_plot(
                pcoa=pcoa,
                metadata_df=metadata_df,
                colouring_variable=str(column),
                shape_variable=None,
                point_size=point_size)

if __name__ == "__main__":
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    pcoa = convert_qiime2_2_skbio(args.pcoa_qza)

    # Load metadata into pandas dataframe
    metadata_df = load_metadata(args.metadata)

    #generate_pcoa_plot(pcoa, metadata_df, args.target_primary)
    output_name = "PCoA_plots_all.pdf"
    save_as_pdf_pages(run_multiple(pcoa, metadata_df, args.point_size),
            filename=output_name,
            path=args.output_dir)
