from qiime2 import Artifact
from qiime2.plugins.taxa.methods import collapse

import pandas as pd
import numpy as np
import re
from plotnine import *

from scripts.qiime2_helper.metadata_helper import (
	load_metadata
)

from scripts.qiime2_helper.artifact_helper import (
	VALID_COLLAPSE_LEVELS,
	check_artifact_type,
	calculate_percent_value,
	rename_taxa
)

from scripts.qiime2_helper.plotnine_helper import (
	add_fill_colours_from_users,
	add_fill_colours_continous,
	add_fill_colours_discrete
)

# Custom exception
from exceptions.exception import AXIOME3Error

def collapse_taxa(feature_table_artifact, taxonomy_artifact, collapse_level="asv"):
	"""
	Collapse feature table to user specified taxa level (ASV by default).

	Input:
		- QIIME2 artifact of type FeatureData[Taxonomy]

	Returns:
		- pd.DataFrame
			(taxa/ASV as rows, samples as columns, numeric index, appends 'Taxon' column)
	"""
	collapse_level = collapse_level.lower()

	if(collapse_level not in VALID_COLLAPSE_LEVELS):
		raise AXIOME3Error("Specified collapse level, {collapse_level}, is NOT valid!".format(collapse_level=collapse_level))

	# handle ASV case
	if(collapse_level == "asv"):
		# By default, feature table has samples as rows, and ASV as columns
		feature_table_df = feature_table_artifact.view(pd.DataFrame)

		# Transpose feature table
		feature_table_df_T = feature_table_df.T

		# By default, taxonomy has ASV as rows, and metadata as columns
		taxonomy_df = taxonomy_artifact.view(pd.DataFrame)

		# Combine the two df (joins on index (ASV))
		combined_df = feature_table_df_T.join(taxonomy_df)

		# Drop "Confidence" column and use numeric index
		final_df = combined_df.drop(["Confidence"], axis="columns").reset_index(drop=True)

		return final_df

	table_artifact = collapse(table=feature_table_artifact, taxonomy=taxonomy_artifact, level=VALID_COLLAPSE_LEVELS[collapse_level])

	# By default, it has samples as rows, and taxa as columns
	collapsed_df = table_artifact.collapsed_table.view(pd.DataFrame)

	# Transpose
	collapsed_df_T = collapsed_df.T

	# Append "Taxon" column
	collapsed_df_T["Taxon"] = collapsed_df_T.index

	# Reset index
	final_df = collapsed_df_T.reset_index(drop=True)

	return final_df

def group_by_taxa(taxa, groupby="phylum", collapse_level="asv"):
	"""
	Extract taxa name from SILVA taxa format at the user specified level.

	Input:
	- taxa: list of SILVA taxa names (pd.Series)
	- groupby: taxa to group by
	- collapse_level: taxa level to collapse feature table at
	"""
	groupby = groupby.lower()
	collapse_level = collapse_level.lower()

	# Taxa to group by should be more general than collapsed level
	# e.g. groupby="asv", collapse_level="phylum" is not allowed
	if(VALID_COLLAPSE_LEVELS[groupby] > VALID_COLLAPSE_LEVELS[collapse_level]):
		raise AXIOME3Error("taxa to groupby must be more general than the taxa to collapse!\nspecified groupby:{groupby}\nspecified collapse level:{collapse_level}"
			.format(
				groupby=groupby,
				collapse_level=collapse_level
			)
		)

	def groupby_helper(taxa_name, groupby):
		"""
		Expected input format: domain;phylum;class ... ;genus;species
		Not all entries may exist
		"""
		split = taxa_name.split(';')

		# If entry does not exist, return it as unclassified
		if(len(split) < VALID_COLLAPSE_LEVELS[groupby]):
			return "unclassified"

		selected = split[VALID_COLLAPSE_LEVELS[groupby] - 1]

		new_taxa = re.sub(r"\s*D_[0-6]__", "", selected)

		return new_taxa

	grouped_taxa = [groupby_helper(t, groupby) for t in taxa]

	return grouped_taxa

def filter_by_keyword(taxa, keyword=None):
	"""
	Filter df by user specified keywordw

	Input:
		- taxa: original taxa name (pd.Series)
		- keyword: keyword string to search

	Returns:
		- boolean; True if match, False otherwise (pd.Series)
	"""
	# If keyword not specified, return all True
	if(keyword is None):
		default = pd.Series([True for i in range(0, taxa.shape[0])])
		default.index = taxa.index

		return default

	match = taxa.str.contains(str(keyword), case=False, regex=False)

	# Raise ValueError if 0 match?
	if(match.any() == False):
		message = "Specified search term, {term}, is NOT found in any entries".format(term=keyword)

		raise AXIOME3Error(message)

	return match

def filter_by_abundance(df, abundance_col, cutoff=0.2):
	"""
	Filter dataframe by a specified column by abundance
	"""
	if(abundance_col not in df.columns):
		raise AXIOME3Error("Column {col} does not exist in the dataframe".format(col=abundance_col))

	filtered_df = df[df[abundance_col] >= cutoff]

	if(filtered_df.shape[0] == 0):
		raise AXIOME3Error("No entries left with {cutoff} abundance threshold".format(cutoff=cutoff))

	return filtered_df

def round_percentage(df, abundance_col, num_decimal=3):
	if(abundance_col not in df.columns):
		raise AXIOME3Error("Column {col} does not exist in the dataframe".format(col=abundance_col))

	# display value in % instead of decimal
	df[abundance_col] = df[abundance_col]*100
	df[abundance_col] = df[abundance_col].round(1)

	return df

def alphabetical_sort_df(df, cols):
	"""
	Alphabetically sort dataframe by a given column

	Input;
		cols: list of columns to sort dataframe by
	"""
	for col in cols:
		if(col not in df.columns):
			raise AXIOME3Error("Column {col} does not exist in the dataframe".format(col=col))

	sorted_df = df.sort_values(by=cols)

	return sorted_df

def prep_bubbleplot(feature_table_artifact_path, taxonomy_artifact_path,
	metadata_path=None, level="asv", groupby_taxa="phylum", abundance_threshold=0.1, keyword=None):
	feature_table_artifact = check_artifact_type(feature_table_artifact_path, "feature_table")
	taxonomy_artifact = check_artifact_type(taxonomy_artifact_path, "taxonomy")
	collapsed_df = collapse_taxa(feature_table_artifact, taxonomy_artifact, level)

	original_taxa = pd.Series(collapsed_df["Taxon"])
	row_id = pd.Series(collapsed_df.index)
	renamed_taxa = rename_taxa(original_taxa, row_id)

	percent_df = calculate_percent_value(collapsed_df.drop(["Taxon"], axis="columns"))
	percent_df["SpeciesName"] = renamed_taxa

	taxa_group = group_by_taxa(original_taxa, groupby_taxa, level)
	percent_df["TaxaGroup"] = taxa_group

	filter_criteria = filter_by_keyword(original_taxa, keyword)
	filtered_df = percent_df.loc[filter_criteria, ]

	long_df = pd.melt(filtered_df, id_vars=['SpeciesName', 'TaxaGroup'], var_name="SampleName", value_name="Percentage")

	abundance_filtered_df = filter_by_abundance(long_df, "Percentage", abundance_threshold)
	rounded_abundance_filtered_df = round_percentage(abundance_filtered_df, "Percentage", 3)
	sorted_df = alphabetical_sort_df(rounded_abundance_filtered_df, ["TaxaGroup", "SpeciesName"])
	# Make SpeciesName column category to avoid automatic sorting
	sorted_df['SpeciesName'] = pd.Categorical(sorted_df['SpeciesName'], categories=sorted_df['SpeciesName'].unique(), ordered=True)
	# Join metadata with bubbleplot df
	if(metadata_path is not None):
		metadata_df = load_metadata(metadata_path)
		merged_df = sorted_df.merge(metadata_df, how="inner", left_on="SampleName", right_index=True)

		return merged_df

	return sorted_df

def make_bubbleplot(df, fill_variable=None,
	palette='Paired', brewer_type='qual', alpha=0.9, stroke=0.6):
	aes_fill = fill_variable if fill_variable is not None else "SampleName"
	ggplot_obj = ggplot(
									df,
									aes(
										x="SampleName",
										y="SpeciesName",
										fill=aes_fill,
										size="Percentage"
									)
								)

	point = geom_point(shape='o', alpha=alpha, stroke=stroke)
	text = geom_text(aes(label="Percentage"), colour="black", size=5)
	scale_size = scale_size_continuous(range=[6, 20])

	y_label = ylab("Taxonomic affiliation")
	main_theme = theme_bw()
	theme_styles = theme(
									axis_text=element_text(size=8, colour='black'),
									text=element_text(size=8, family='Arial', colour='black'),
									axis_text_x=element_text(angle=90),
									plot_title=element_text(hjust=0.5),
									legend_title=element_text(size=10, face='bold'),
									legend_key=element_blank(),
									legend_text=element_text(size=10),
									legend_key_size=20,
									strip_text_y = element_text(angle = 0),
									panel_spacing=0,
									strip_background=element_blank()									)

	size_guide = guides(size=False)
	if(fill_variable is not None):
		fill_guide = guides(fill=guide_legend(override_aes = {'size': 5}))
	else:
		fill_guide = guides(fill=False)
	plot_theme = main_theme + theme_styles

	bubble_plot = ggplot_obj + point + text + scale_size + y_label + theme_styles + size_guide + fill_guide

	# Add custom fill
	if(fill_variable is not None):
		if(pd.api.types.is_numeric_dtype(df[fill_variable])):
			bubble_plot = add_fill_colours_continous(bubble_plot, str(fill_variable))
		else:
			if(len(df[fill_variable].unique()) > 12):
				bubble_plot = add_fill_colours_discrete(bubble_plot, str(fill_variable))
			else:
				bubble_plot = add_fill_colours_from_users(bubble_plot, str(fill_variable), palette, brewer_type)

	return bubble_plot

def save_plot(plot, filename="plot", output_dir='.',
	file_format='pdf', width=200, height=200, units='mm'):
	# Add extension to file name
	fname = filename + "." + file_format

	plot.save(
		filename=fname,
		format=file_format,
		path=output_dir,
		width=width,
		height=height,
		units=units
	)

#feature_table_artifact_path = "/data/output/dada2/dada2_table.qza"
#taxonomy_artifact_path = "/data/output/taxonomy/taxonomy.qza"
#metadata_path = "/data/metadata_MaCoTe.tsv"
#df = prep_bubbleplot(feature_table_artifact_path, taxonomy_artifact_path,metadata_path, "asv")
#plot = make_bubbleplot(df, fill_variable="NTCGroup")
#save_plot(plot)