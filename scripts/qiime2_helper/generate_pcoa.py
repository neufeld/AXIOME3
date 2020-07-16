"""
Modified version of Jackson Tsuji of Neufeld Research Group's script to make PCoA plot.

Written by Daniel Min, Neufeld Research Group, 2019
"""
from skbio.stats import ordination
from qiime2 import (
    Artifact,
    Metadata
)
import sys
import os
import pandas as pd
from plotnine import *

from scripts.qiime2_helper.metadata_helper import (
    load_metadata,
    convert_col_dtype
)

# Colour formatters
formatters = {
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'REVERSE': '\033[7m',
        'UNDERLINE': '\033[4m',
        'END': '\033[0m'
        }

def convert_qiime2_2_skbio(pcoa_artifact):
    """
    Convert QIIME2 PCoA artifact to skbio OrdinationResults object.

    ** Will throw errors if the artifact type is NOT PCoAResults **
    You may check Artifact type by checking the "type" property of the Artifact
    object after loading the artifact via 'Artifact.load(artifact)'
    """
    try:
        pcoa_artifact = Artifact.load(pcoa_artifact)

        # Check Artifact type
        if(str(pcoa_artifact.type) != "PCoAResults"):
            msg = "Input QIIME2 Artifact is not of the type 'PCoAResults'!"
            raise ValueError(msg)

        pcoa = pcoa_artifact.view(ordination.OrdinationResults)
    except ValueError:
        raise

    # Rename PCoA coordinates index (so left join can be performed later)
    coords = pcoa.samples

    coords.index.names = ['SampleID']

    # Rename columns to have more meaningful names
    num_col = coords.shape[1]
    col_names = ['PC'+str(i) for i in range(1, num_col+1)]
    coords.columns = col_names

    pcoa.samples = coords

    return pcoa

# Add a custom colour scale onto a plotnine ggplot
def add_discrete_fill_colours(plot, n_colours, name):
    n_colours = int(n_colours)

    if n_colours <= 8:
        plot = plot + scale_fill_brewer(type='qual',palette='Set1',name=name)
    elif (n_colours >= 9) & (n_colours <= 12):
        plot = plot + scale_fill_brewer(type='qual',palette='Paired',name=name)
    elif n_colours > 12:
        plot = plot

    return(plot)

# Add a custom colour scale onto a plotnine ggplot
def add_fill_colours_from_users(plot, name, palette='Paired', brewer_type='qual'):
    plot = plot + scale_fill_brewer(type=brewer_type, palette=palette, name=name)


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

def generate_pcoa_plot(
    pcoa,
    metadata,
    colouring_variable,
    shape_variable=None,
    primary_dtype="category",
    secondary_dtype="category",
    palette='Paired',
    brewer_type='qual',
    alpha=0.9,
    stroke=0.6,
    point_size=6,
    x_axis_text_size=10,
    y_axis_text_size=10,
    legend_title_size=10,
    legend_text_size=10,
    PC_axis1='PC1',
    PC_axis2='PC2'):

    # Load metadata file
    metadata_df = load_metadata(metadata)
    
    # Inner join metadata file with ordinations
    pcoa_coords = pcoa.samples
    pcoa_data_samples = pd.merge(
            pcoa_coords,
            right=metadata_df,
            left_index=True,
            right_index=True)

    # Make x and y axis labels
    proportions = pcoa.proportion_explained

    x_explained_idx = int(PC_axis1.replace('PC', '')) - 1
    y_explained_idx = int(PC_axis2.replace('PC', '')) - 1

    x_explained = str(round(proportions[x_explained_idx] * 100, 1))
    y_explained = str(round(proportions[y_explained_idx] * 100, 1))

    # Convert user specified columns to category
    # **BIG ASSUMPTION HERE**
    pcoa_data_samples = convert_col_dtype(
            pcoa_data_samples,
            colouring_variable,
            primary_dtype)

    if(shape_variable is not None):
        pcoa_data_samples = convert_col_dtype(
                pcoa_data_samples,
                shape_variable,
                secondary_dtype)

    # Pre-format target variables
    #primary_target_fill = 'factor(' + str(colouring_variable) + ')'
    primary_target_fill = str(colouring_variable)

    if(shape_variable is not None):
        secondary_target_fill = str(shape_variable)

        ggplot_obj = ggplot(pcoa_data_samples,
                        aes(x=PC_axis1,
                            y=PC_axis2,
                            fill=primary_target_fill,
                            shape=secondary_target_fill))
    else:
        ggplot_obj = ggplot(pcoa_data_samples,
                        aes(x=PC_axis1,
                            y=PC_axis2,
                            fill=primary_target_fill))

    # Plot the data
    pcoa_plot = (ggplot_obj
    + geom_point(size=point_size, alpha=alpha, stroke=stroke)
    + theme_bw()
    + theme(panel_grid=element_blank(), 
            line=element_line(colour='black'),
           panel_border=element_rect(colour='black'),
           legend_title=element_text(size=legend_title_size, face='bold'),
           legend_key=element_blank(),
           legend_text=element_text(size=legend_text_size),
           axis_title_x=element_text(size=x_axis_text_size),
           axis_title_y=element_text(size=y_axis_text_size),
           legend_key_height=5,
           text=element_text(family='Arial', colour='black'))
    + xlab(PC_axis1 + ' (' + x_explained + '%)')
    + ylab(PC_axis2 + ' (' + y_explained + '%)'))

    # Custom colours
    color_len = len(pcoa_data_samples[colouring_variable].unique())
    color_name = str(colouring_variable)
    pcoa_plot = add_fill_colours_from_users(pcoa_plot, color_name, palette, brewer_type)

    # Custom shapes
    if(shape_variable is not None):
        shape_len = len(pcoa_data_samples[shape_variable].unique())
        shape_name = str(shape_variable)

        pcoa_plot = add_discrete_shape(pcoa_plot, shape_len, shape_name)

    return pcoa_plot

def save_plot(pcoa_plot, filename, output_dir='.',
    file_format='pdf', width=100, height=90, units='mm'):
    
    # Save the plot
    # Add .pdf extension if not specified or other extensions are provided
    #if not (filename.endswith('.pdf')):
    #    file_name, file_ext = os.path.splitext(filename)

    #    # Replace extension with .pdf if exists and not .pdf
    #    if(file_ext and file_ext != '.pdf'):
    #        filename = file_name + '.pdf'
    #    # Add .pdf if extension does not exist
    #    else:
    #        filename = filename + '.pdf'

    # Add extension to file name
    fname = filename + "." + file_format

    # Plot size
    pdf_width_mm = width
    pdf_height_mm = height

    pcoa_plot.save(
             filename=fname,
             format=file_format,
             path=output_dir,
             width=pdf_width_mm,
             height=pdf_height_mm,
             units=units)