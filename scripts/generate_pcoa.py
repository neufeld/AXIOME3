from argparse import ArgumentParser
from skbio.stats import ordination
from qiime2 import Artifact
import sys
import os
import pandas as pd
from plotnine import *

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

    parser.add_argument('--target-primary', help="""
            Primary target column to use for PCoA plot. Uses colors as
            levels.
            """,
            required=True)

    parser.add_argument('--target-secondary', help="""
            Second target column to use for PCoA plot. Uses shapes as levels
            """,
            default=None)

    parser.add_argument('--point-size', help="""
            Geom_point size. Default 6
            """,
            type=int,
            default=6)

    return parser

def convert_qiime2_2_skbio(pcoa_artifact):
    """
    Convert QIIME2 PCoA artifact to skbio OrdinationResults object.
    """
    pcoa = Artifact.load(pcoa_artifact).view(ordination.OrdinationResults)

    # Rename PCoA coordinates index (so left join can be performed later)
    coords = pcoa.samples

    coords.index.names = ['SampleID']

    # Rename columns to have more meaningful names
    num_col = coords.shape[1]
    col_names = ['PC'+str(i) for i in range(1, num_col+1)]
    coords.columns = col_names

    pcoa.samples = coords

    return pcoa

def load_metadata(metadata_path):
    # Load metadata into pandas dataframe
    metadata_df = pd.read_csv(metadata_path, sep='\t', comment='#', index_col=0)
    # Rename index
    metadata_df.index.names = ['SampleID']
    # Replace space characters with underscore
    metadata_df.columns = metadata_df.columns.str.replace(' ', '_')

    return metadata_df

# Add a custom colour scale onto a plotnine ggplot
def add_discrete_fill_colours(plot, n_colours, name):
    n_colours = int(n_colours)

    if n_colours <= 8:
        plot = plot + scale_fill_brewer(type='qual',palette='Set1',name=name)
    elif (n_colours >= 9) & (n_colours <= 12):
        plot = plot + scale_fill_brewer(type='qual',palette='Set3',name=name)
    elif n_colours > 12:
        plot = plot

    return(plot)

# Add a custom shape scale
def add_discrete_shape(plot, n_shapes, name):
    # circle, square, triangle, diamond, reverse triangle, star, plus, x
    markers = ['o', 's', '^', 'd', 'v', '*', '+', 'x']
    # Use alphabets if viable markers to use run out
    alphabets = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    alphabet_markers = ['$' + letter + '$' for letter in alphabets]
    markers.extend(alphabet_markers)

    plot = plot + scale_shape_manual(values=markers[0:n_shapes], name=name)

    return plot

def generate_pcoa_plot(pcoa,
        metadata_df,
        colouring_variable,
        shape_variable=None,
        point_size=6):

    # Left join metadata file with ordinations
    pcoa_coords = pcoa.samples
    pcoa_data_samples = pd.merge(
            pcoa_coords,
            right=metadata_df,
            left_index=True,
            right_index=True)

    # Make x and y axis labels
    proportions = pcoa.proportion_explained

    x_explained = str(round(proportions[0] * 100, 1))
    y_explained = str(round(proportions[1] * 100, 1))

    # Make sure user specified target columns actually exist in the dataframe
    colouring_variable = colouring_variable.replace(' ', '_')
    shape_variable = shape_variable.replace(' ', '_') \
            if shape_variable != None \
            else None

    if(colouring_variable not in pcoa_data_samples.columns):
        msg = "Column '{column}' does NOT exist in the metadata!".format(
                column=colouring_variable
                )

        raise ValueError(msg)

    if(shape_variable is not None and
            shape_variable not in pcoa_data_samples.columns):
        msg = "Column '{column}' does NOT exist in the metadata!".format(
                column=shape_variable
                )

        raise ValueError(msg)

    # Pre-format target variables
    primary_target_fill = 'factor(' + str(colouring_variable) + ')'

    if(shape_variable is not None):
        secondary_target_fill = 'factor(' + str(shape_variable) + ')'

        ggplot_obj = ggplot(pcoa_data_samples,
                        aes(x='PC1',
                            y='PC2',
                            fill=primary_target_fill,
                            shape=secondary_target_fill))
    else:
        ggplot_obj = ggplot(pcoa_data_samples,
                        aes(x='PC1',
                            y='PC2',
                            fill=primary_target_fill))

    # Plot the data
    pcoa_plot = (ggplot_obj
    + geom_point(size=point_size, alpha=0.6, stroke=0.5)
    + theme_bw()
    + theme(panel_grid=element_blank(), 
            line=element_line(colour='black'),
           panel_border=element_rect(colour='black'),
           legend_title=element_text(size=10, face='bold'),
           legend_key=element_blank(),
           legend_key_height=5,
           text=element_text(family='Arial', colour='black'))
    + xlab('PC1 (' + x_explained + '%)')
    + ylab('PC2 (' + y_explained + '%)'))

    # Custom colours
    color_len = len(pcoa_data_samples[colouring_variable].unique())
    color_name = str(colouring_variable)
    pcoa_plot = add_discrete_fill_colours(pcoa_plot, color_len, color_name)

    # Custom shapes
    if(shape_variable is not None):
        shape_len = len(pcoa_data_samples[shape_variable].unique())
        shape_name = str(shape_variable)

        pcoa_plot = add_discrete_shape(pcoa_plot, shape_len, shape_name)

    return pcoa_plot

if __name__ == "__main__":
    parser = args_parse()

    # Print help messages if no arguments are supplied
    if( len(sys.argv) < 2):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Load QIIME2 PCoA result and convert to PCoA object
    pcoa = convert_qiime2_2_skbio(args.pcoa_qza)

    # Load metadata
    metadata_df = load_metadata(args.metadata)

    pcoa_plot = generate_pcoa_plot(
            pcoa = pcoa,
            metadata_df = metadata_df,
            colouring_variable = args.target_primary,
            shape_variable = args.target_secondary,
            point_size = args.point_size)

    # Save the plot
    output_pdf_filepath = "PCoA_plot.pdf"
    # Plot size
    pdf_width_mm = 100
    pdf_height_mm = 90

    pcoa_plot.save(
             output_pdf_filepath,
             width=pdf_width_mm,
             height=pdf_height_mm,
             units='mm')
