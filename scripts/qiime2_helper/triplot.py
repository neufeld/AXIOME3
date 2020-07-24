import os
import re
import numpy as np
import pandas as pd
from plotnine import *

from qiime2 import (
	Artifact,
	Metadata
)
from qiime2.plugins.taxa.methods import collapse

from rpy2.robjects.vectors import IntVector
from rpy2.robjects.packages import importr
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter

from scripts.qiime2_helper.metadata_helper import (
	load_metadata,
	load_env_metadata,
	convert_col_dtype
)

from scripts.qiime2_helper.artifact_helper import (
	check_artifact_type
)

from scripts.qiime2_helper.rpy2_helper import (
	convert_pd_df_to_r,
	convert_r_matrix_to_r_df,
	convert_r_df_to_pd_df
)

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

	VALID_LEVELS = {
		"domain": 1, 
		"phylum": 2,
		"class": 3,
		"order": 4, 
		"familiy": 5, 
		"genus": 6, 
		"species": 7,
		"asv": 8
	}

	if(collapse_level not in VALID_LEVELS):
		raise ValueError("Specified collapse level, {collapse_level}, is NOT valid!".format(collapse_level=collapse_level))

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

	table_artifact = collapse(table=feature_table_artifact, taxonomy=taxonomy_artifact, level=VALID_LEVELS[collapse_level])

	# By default, it has samples as rows, and taxa as columns
	collapsed_df = table_artifact.collapsed_table.view(pd.DataFrame)

	# Transpose
	collapsed_df_T = collapsed_df.T

	# Append "Taxon" column
	collapsed_df_T["Taxon"] = collapsed_df_T.index

	# Reset index
	final_df = collapsed_df_T.reset_index(drop=True)

	return final_df

def rename_taxa(taxa, row_id):
	"""
	Clean up SILVA taxonomic names

	Input:
	- taxa: list of SILVA taxa names (pd.Series)
	- row_id: row ID (pd.Series)
	"""
	taxa_with_id = taxa.astype(str) + "_" + row_id.astype(str)

	new_taxa = [re.sub(r";\s*Ambiguous_taxa", "", t) for t in taxa_with_id]
	new_taxa = [re.sub(r"(;\s*D_[2-6]__uncultured[^;_0-9]*)", "", t) for t in new_taxa]
	new_taxa = [re.sub(r"\s*D_[0-6]__", "", t) for t in new_taxa]

	# get the last entry
	new_taxa = [re.sub(r".*;", "", t) for t in new_taxa]

	return new_taxa

def filter_by_abundance(df, abundance_threshold=0.1, percent_axis=0, filter_axis=1):
	"""
	Calculates taxa percent abundance per sample. (taxa abundance / overall abundance in a sample).

	Input:
		- df: pandas dataframe describing taxa/ASV abundance per sample.
		- abundance_threshold: % value threshold (0: 0% cutoff, 1: 100% cutoff)
		- percent_axis: axis used to calculate % abundance
		- filter_axis: axis used to filter (filter if at least one of the samples has % abundance >= threshold)

		If samples as columns, and taxa/ASV as rows, do percent_axis=0, filter_axis=1.
		If samples as rows, and taxa/ASV as columns, do percent_axis=1, filter_axis=0.

		Default options assume samples as columns and taxa/ASV as rows.
	"""
	percent_df = calculate_percent_value(df, percent_axis)

	# keep taxa/ASVs if at least one of the samples has % abundance >= threshold
	to_keep = (percent_df >= abundance_threshold).any(filter_axis)

	# Raise error if no entries after filtering?
	if(to_keep.any() == False):
		raise ValueError("Zero entries after filtering by abundance at {} threshold".format(abundance_threshold))

	# Note that original row index should preserved.
	# Will be buggy if row index is reindexed. (add test case for this?)
	filtered = df.loc[to_keep, ]

	return filtered

def calculate_percent_value(df, axis=0):
	"""
	(value / column (row) sum)
	Column by default.
	"""

	def percent_value_operation(x):
		"""
		Custom function to be applied on pandas dataframe.

		Input:
				x: pandas series; numerical data
		"""
		series_length = x.size
		series_sum = x.sum()

		# percent value should be zero if sum is 0
		all_zeros = np.zeros(series_length)
		percent_values = x / series_sum if series_sum != 0 else pd.Series(all_zeros)

		return percent_values

	# Calculate % value
	percent_val_df = df.apply(lambda x: percent_value_operation(x), axis=axis)

	return percent_val_df

def filter_by_total_count(feature_table_df, sum_axis=1):
	"""
	Remove samples that have total counts <= 5 (R complains if total count <= 5)

	Inputs
		- feature_table_df: feature table in pandas DataFrame
		- sum_axis: axis to sum over.
			Do axis=0 if sample as columns, taxa/ASV as rows (index)
			Do axis=1 if sample as rows (index), taxa/ASV as columns

	Default option assumes sample as row (index), taxa/ASV as columns
	"""
	row_sum = feature_table_df.sum(sum_axis)

	to_keep = row_sum > 5

	filtered_df = feature_table_df.loc[to_keep, ]

	return filtered_df

def find_sample_intersection(feature_table_df, sample_metadata_df, environmental_metadata_df):
	"""
	Find intersection of feature table, sample metadata, and environmental metadata.

	Inputs:
		- feature_table_df: feature table in pandas DataFrame (samples as row, taxa/ASV as columns)
		- sample_metadata_df: sample metadata in pandas DataFrame (samples as row, metadata as columns)
		- environmental_metadata_df: environmental metadata in pandas DataFrame (samples as row, metadata as columns)

		Assumes sampleID as index
	"""
	combined_df = pd.concat([feature_table_df, sample_metadata_df, environmental_metadata_df], join="inner", axis=1)

	intersection_samples = combined_df.index

	if(len(intersection_samples) == 0):
		raise ValueError("Feature table, sample metadata, and environmental metadata do NOT share any samples...")

	intersection_feature_table_df = feature_table_df.loc[intersection_samples, ]
	intersection_sample_metadata_df = sample_metadata_df.loc[intersection_samples, ]
	intersection_environmental_metadata_df = environmental_metadata_df.loc[intersection_samples, ]

	return intersection_feature_table_df, intersection_sample_metadata_df, intersection_environmental_metadata_df

def calculate_dissimilarity_matrix(feature_table, method="bray"):
	"""
	Calculates dissimilarity matarix using the feature table.
	It uses R's vegan package (using rpy2 interface)

	Inputs:
		- feature_table_df: feature table (rpy2.robjects)
		- method: dissimilarity index (see 'vegdist' R documentation for supported methods)

	Outputs:
		- distance matrix (rpy2.robjects)
	"""
	vegan = importr('vegan')

	return vegan.vegdist(feature_table, method)

def calculate_ordination(dissimilarity_matrix):
	"""
	Calculates ordination.
	It uses R's stats package (using rpy2 interface)

	Inputs:
		- dissimilarity_matrix: distance matrix of type rpy2.robjects.

	Outputs:
		- ordination (rpy2.robjects.)
	"""
	stats = importr('stats')

	ordination = stats.cmdscale(dissimilarity_matrix, k=10, eig=True)

	return ordination

def calculate_weighted_average(ordination, feature_table):
	"""
	Calculate weighted average scores of each taxa/ASV onto ordination
	"""
	vegan = importr('vegan')

	points = ordination[ordination.names.index('points')]

	wascores = vegan.wascores(points, feature_table)

	return wascores

def project_env_metadata_to_ordination(ordination, env_metadata):
	"""

	"""
	vegan = importr('vegan')

	projection = vegan.envfit(ordination, env_metadata, choices=IntVector((1,2)))

	return projection

def combine_projection_arrow_with_r_sqr(projection):
	"""
	Cbind R2 with arrow matrix
	"""
	base = importr('base')

	projection_vectors = projection[projection.names.index('vectors')]
	arrow = projection_vectors[projection_vectors.names.index('arrows')]
	r_sqr = projection_vectors[projection_vectors.names.index('r')]

	projection_matrix = base.cbind(arrow, R2=r_sqr)

	return projection_matrix

def generate_vector_arrow_df(projection_df, R2_threshold):
	"""
	Generate vector arrows to overlay on triplot, and optionally filter it by user specified threshold

	Inputs:
		- projection_df: pandas DataFrame
			environmental variables as row, PC dimensions and R2 value as columns

	Returns:
		- pandas DataFrame
			environmental variables as row, PC dimensions as columns (labeled as PC1, PC2, ...)
	"""
	#if((projection_df['R2'] > R2_threshold).any() == False):
	#	raise ValueError("No entries left after applying R2 threshold, {}".format(R2_threshold))

	filtered_df = projection_df.loc[(projection_df['R2'] > R2_threshold), ]
	vector_arrow_df = filtered_df.drop(columns=['R2'])
	vector_arrow_df = vector_arrow_df.mul(np.sqrt(filtered_df['R2']), axis=0)

	return vector_arrow_df

def rename_as_PC_columns(df):
	"""
	Rename pandas DataFrame column names as PC1, PC2, ...
	"""
	num_col = df.shape[1]
	if(num_col == 0):
		raise ValueError("Specified dataframe has zero columns...")

	new_col_names = ['PC' + str(i) for i in range(1, num_col+1)]
	df.columns = new_col_names

	return df

def normalized_taxa_total_abundance(wascores_df, feature_table_df):
	"""
	Calculate normalized, total abundance of each taxa

	Inputs:
		- wascores_df: weighted average scores in pandas DataFrame (taxa as index, coordinates as columns)
		- feature_table_df: feature table in pandas DataFrame (sample as index, taxa as columns)
	"""
	total_abundance = feature_table_df.to_numpy().sum()
	taxa_count = feature_table_df.sum(axis=0)
	# pandas treats 0/0 as 0 (does not raise ZeroDivisionError)
	normalized_taxa_count = taxa_count / total_abundance
	wascores_df['abundance'] = normalized_taxa_count

	return wascores_df

def filter_by_wascore_threshold(normalized_wascores_df, wa_threshold):
	"""
	Filter weighted average DataFrame by normalized abundance
	"""
	if('abundance' not in normalized_wascores_df.columns):
		raise ValueError("normalized taxa count column does not exist")

	filtered_df = normalized_wascores_df[normalized_wascores_df['abundance'] > wa_threshold]

	return filtered_df

def get_variance_explained(eig_vals):
	"""
	Calculate proportion explained per PC axis

	Inputs:
		- eig_vals: eigenvalues per PC axis. pandas Series
	"""

	num_row = eig_vals.shape[0]
	total_variance = eig_vals.sum()
	proportion_explained = eig_vals / total_variance
	proportion_explained = proportion_explained * 100

	new_index_names = ['PC' + str(i) for i in range(1, num_row+1)]
	proportion_explained.index = new_index_names
	proportion_explained.columns = ['proportion_explained']
	
	return proportion_explained

def prep_triplot_input(sample_metadata_path, env_metadata_path, feature_table_artifact_path,
	taxonomy_artifact_path, collapse_level="asv", abundance_threshold=0.1, R2_threshold=0.1, wa_threshold=0.1):

	# Load sample metadata
	sample_metadata_df = load_metadata(sample_metadata_path)
	# Load environmental metadata
	# and drop rows with missing values (WARN users?)
	env_metadata_df = load_env_metadata(env_metadata_path)
	env_metadata_df = env_metadata_df.dropna()

	# Load feature table and collapse
	feature_table_artifact = check_artifact_type(feature_table_artifact_path, "feature_table")
	taxonomy_artifact = check_artifact_type(taxonomy_artifact_path, "taxonomy")
	collapsed_df = collapse_taxa(feature_table_artifact, taxonomy_artifact, collapse_level)

	original_taxa = pd.Series(collapsed_df["Taxon"])
	row_id = pd.Series(collapsed_df.index)
	renamed_taxa = rename_taxa(original_taxa, row_id)

	# filter by abundance
	taxa_index_collapsed_df = collapsed_df
	taxa_index_collapsed_df['Taxa'] = renamed_taxa
	taxa_index_collapsed_df = taxa_index_collapsed_df.set_index('Taxa')
	abundance_filtered_df = filter_by_abundance(
		df=taxa_index_collapsed_df.drop(['Taxon'], axis="columns"),
		abundance_threshold=abundance_threshold,
		percent_axis=0,
		filter_axis=1
	)

	# transpose feature table so that it has samples as rows, taxa/ASV as columns
	transposed_df = abundance_filtered_df.T

	# Remove samples that have total counts <= 5 (R complains if total count <= 5)
	count_filtered_df = filter_by_total_count(transposed_df)

	# Find sample intersection of feature table, sample metadata, and environmental metadata
	intersection_feature_table_df, intersection_sample_metadata_df, intersection_environmental_metadata_df = find_sample_intersection(
		count_filtered_df,
		sample_metadata_df,
		env_metadata_df
	)

	r_feature_table = convert_pd_df_to_r(intersection_feature_table_df)

	r_dissimilarity_matrix = calculate_dissimilarity_matrix(r_feature_table)

	ordination = calculate_ordination(r_dissimilarity_matrix)

	wascores = calculate_weighted_average(ordination, r_feature_table)

	r_env_metadata = convert_pd_df_to_r(intersection_environmental_metadata_df)
	projection = project_env_metadata_to_ordination(ordination, r_env_metadata)

	# convert to pandas DataFrame
	ordination_point_df = convert_r_df_to_pd_df(convert_r_matrix_to_r_df(ordination[ordination.names.index('points')]))
	ordination_eig_df = convert_r_df_to_pd_df(convert_r_matrix_to_r_df(ordination[ordination.names.index('eig')]))
	wascores_df = convert_r_df_to_pd_df(convert_r_matrix_to_r_df(wascores))
	
	projection_df = convert_r_df_to_pd_df(convert_r_matrix_to_r_df(combine_projection_arrow_with_r_sqr(projection)))

	# generate vector arrows
	vector_arrow_df = generate_vector_arrow_df(projection_df, R2_threshold)

	# Rename dataframe columns
	renamed_ordination_point_df = rename_as_PC_columns(ordination_point_df)
	renamed_wascores_df = rename_as_PC_columns(wascores_df)
	renamed_vector_arrow_df = rename_as_PC_columns(vector_arrow_df)

	# Add normalized taxa count and filter by user specifed thresehold
	normalized_wascores_df = normalized_taxa_total_abundance(renamed_wascores_df, intersection_feature_table_df)
	filtered_wascores_df = filter_by_wascore_threshold(normalized_wascores_df, wa_threshold)

	# Proportion explained
	proportion_explained = get_variance_explained(ordination_eig_df)

	# Combine ordination df and sample metadata df
	merged_df = renamed_ordination_point_df.join(intersection_sample_metadata_df, how="inner")

	return merged_df, renamed_vector_arrow_df, filtered_wascores_df, proportion_explained

def make_triplot(merged_df, vector_arrow_df, wascores_df, proportion_explained,
	fill_variable, PC_axis_one='PC1', PC_axis_two='PC2'):
	"""

	"""
	# Remove unused categories
	merged_df[fill_variable] = merged_df[fill_variable].cat.remove_unused_categories()

	# Plot the data
	base_plot = ggplot(
		merged_df, 
		aes(
			x=PC_axis_one,
			y=PC_axis_two,
			label=merged_df.index,
			fill=fill_variable
		)
	)
	base_points = geom_point(size=4)

	base_anno = geom_text(size=4)

	PC_axis_one_variance = str(round(proportion_explained.loc[PC_axis_one, 'proportion_explained'],2))
	PC_axis_two_variance = str(round(proportion_explained.loc[PC_axis_two, 'proportion_explained'],2))
	x_label_placeholder = PC_axis_one + "(" + PC_axis_one_variance + "%)"
	y_label_placeholder = PC_axis_two + "(" + PC_axis_two_variance + "%)"
	x_lab = xlab(x_label_placeholder)
	y_lab = ylab(y_label_placeholder)

	my_themes = theme(
		panel_grid=element_blank(), # No grid
		panel_border=element_rect(colour='black'), # black outline
		legend_key=element_blank(), # No legend background
		aspect_ratio=1
	)

	plot = (base_plot + 
		base_points + 
		#base_anno +  
		x_lab + 
		y_lab + 
		theme_bw() + 
		my_themes)

	# Taxa points
	if(wascores_df.shape[0] > 0):
		taxa_points = geom_point(
			aes(
				x=PC_axis_one,
				y=PC_axis_two,
				size='abundance'
			),
			colour="black",
			fill='none',
			data=wascores_df,
			stroke=0.1,
			inherit_aes=False,
			show_legend=False
		)

		# Taxa annotation
		taxa_anno = geom_text(
			aes(
				x=PC_axis_one,
				y=PC_axis_two,
				label=wascores_df.index
			),
			data=wascores_df,
			inherit_aes=False,
			size=4
		)

		plot = plot + taxa_points + scale_size_area(max_size=15) + taxa_anno

	# if vector arrows pass the thresohld
	if(vector_arrow_df.shape[0] > 0):
		env_arrow = geom_segment(
			aes(
				x=0,
				xend=PC_axis_one,
				y=0,
				yend=PC_axis_two,
				colour=vector_arrow_df.index
			),
			data=vector_arrow_df,
			arrow=arrow(length=0.1),
			inherit_aes=False,
			show_legend=False
		)

		env_anno = geom_text(
			aes(
				x=PC_axis_one,
				y=PC_axis_two,
				label=vector_arrow_df.index,
				colour=vector_arrow_df.index
			),
			size=4,
			data=vector_arrow_df,
			inherit_aes=False,
			show_legend=False
		)

		plot = plot + env_arrow + env_anno

	return plot

def save_plot(plot, filename, output_dir='.',
		file_format='pdf', width=100, height=100, units='mm'):

	fname = filename + "." + file_format

	plot.save(
		filename=fname,
		format=file_format,
		path=output_dir,
		width=width,
		height=height,
		units=units
	)

#feature_table_artifact_path = "/backend/triplot/merged_table.qza"
#taxonomy_artifact_path = "/backend/triplot/taxonomy.qza"
#sample_metadata_path = "/backend/triplot/modified_aq_survey_metadata_triplots.txt"
#env_metadata_path = "/backend/triplot/aq_survey_env_num.txt"
#merged_df, vector_arrow_df, wascores_df, proportion_explained = prep_triplot_input(
#	sample_metadata_path,
#	env_metadata_path,
#	feature_table_artifact_path,
#	taxonomy_artifact_path,
#	collapse_level="phylum",
#	abundance_threshold=0.2,
#	R2_threshold=0.05
#)
#triplot = make_triplot(merged_df, vector_arrow_df, wascores_df, proportion_explained, fill_variable="I5_Index_ID")
#save_plot(triplot, "plot")