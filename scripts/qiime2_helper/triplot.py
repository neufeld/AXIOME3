import os
import pandas as pd
import numpy as np
from plotnine import *

from qiime2 import (
	Artifact,
	Metadata
)
from qiime2.plugins.taxa.methods import collapse

from rpy2.robjects.vectors import IntVector
from rpy2.robjects.packages import importr
import rpy2.robjects as ro

from scripts.qiime2_helper.metadata_helper import (
	load_metadata,
	load_env_metadata,
	convert_col_dtype
)

from scripts.qiime2_helper.artifact_helper import (
	VALID_COLLAPSE_LEVELS,
	check_artifact_type,
	filter_by_abundance,
	rename_taxa
)

from scripts.qiime2_helper.rpy2_helper import (
	VEGDIST_OPTIONS,
	convert_pd_df_to_r,
	convert_r_matrix_to_r_df,
	convert_r_df_to_pd_df
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

def find_sample_intersection(feature_table_df, abundance_df, sample_metadata_df, environmental_metadata_df):
	"""
	Find intersection of feature table, sample metadata, and environmental metadata.

	Inputs:
		- feature_table_df: feature table in pandas DataFrame (samples as row, taxa/ASV as columns)
		- abundance_df: feature table in pandas DataFrame (samples as row, taxa/ASV as columns; to overlay as taxa bubbles later)
		- sample_metadata_df: sample metadata in pandas DataFrame (samples as row, metadata as columns)
		- environmental_metadata_df: environmental metadata in pandas DataFrame (samples as row, metadata as columns)

		Assumes sampleID as index
	"""
	combined_df = pd.concat([feature_table_df, abundance_df, sample_metadata_df, environmental_metadata_df], join="inner", axis=1)

	intersection_samples = combined_df.index

	if(len(intersection_samples) == 0):
		raise AXIOME3Error("Feature table, sample metadata, and environmental metadata do NOT share any samples...")

	intersection_feature_table_df = feature_table_df.loc[intersection_samples, ]
	intersection_abundance_df = abundance_df.loc[intersection_samples, ]
	intersection_sample_metadata_df = sample_metadata_df.loc[intersection_samples, ]
	intersection_environmental_metadata_df = environmental_metadata_df.loc[intersection_samples, ]

	return intersection_feature_table_df, intersection_abundance_df, intersection_sample_metadata_df, intersection_environmental_metadata_df

def calculate_dissimilarity_matrix(feature_table, method="Bray-Curtis"):
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

	if (method not in VEGDIST_OPTIONS):
		raise AXIOME3Error("Specified dissmilarity method, {method} is not supported!".format(method=method))

	return vegan.vegdist(feature_table, VEGDIST_OPTIONS[method])

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

def project_env_metadata_to_ordination(ordination, env_metadata, PC_axis_one, PC_axis_two):
	"""

	"""
	vegan = importr('vegan')

	pc_axes = (PC_axis_one, PC_axis_two)

	projection = vegan.envfit(ordination, env_metadata, choices=IntVector(pc_axes))

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

def rename_as_PC_columns(df, PC_axis_one=None, PC_axis_two=None):
	"""
	Rename pandas DataFrame column names as PC1, PC2, ...
	"""
	# Special case for environmental projection df
	# It needs to be hardcoded because of the way df is created (refer to 'project_env_metadata_to_ordination()'')
	if(PC_axis_one is not None and PC_axis_two is not None):
		new_col_names = ['PC' + str(PC_axis_one), 'PC' + str(PC_axis_two)]
		df.columns = new_col_names

		return df

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
		raise AXIOME3Error("normalized taxa count column does not exist")

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
	taxonomy_artifact_path, ordination_collapse_level="asv", wascores_collapse_level="phylum",
	dissmilarity_index="Bray-Curtis", abundance_threshold=0.1, R2_threshold=0.1,
	wa_threshold=0.1, PC_axis_one=1, PC_axis_two=2):

	# Load sample metadata
	sample_metadata_df = load_metadata(sample_metadata_path)
	# Load environmental metadata
	# and drop rows with missing values (WARN users?)
	env_metadata_df = load_env_metadata(env_metadata_path)
	env_metadata_df = env_metadata_df.dropna()

	# Load feature table and collapse
	feature_table_artifact = check_artifact_type(feature_table_artifact_path, "feature_table")
	taxonomy_artifact = check_artifact_type(taxonomy_artifact_path, "taxonomy")
	ordination_collapsed_df = collapse_taxa(feature_table_artifact, taxonomy_artifact, ordination_collapse_level)
	abundance_collapsed_df = collapse_taxa(feature_table_artifact, taxonomy_artifact, wascores_collapse_level)

	# Rename taxa for wascores collapsed df
	original_taxa = pd.Series(abundance_collapsed_df["Taxon"])
	row_id = pd.Series(abundance_collapsed_df.index)
	renamed_taxa = rename_taxa(original_taxa, row_id)

	abundance_collapsed_df['Taxa'] = renamed_taxa
	abundance_collapsed_df_reindexed = abundance_collapsed_df.set_index('Taxa')
	abundance_collapsed_df_reindexed = abundance_collapsed_df_reindexed.drop(['Taxon'], axis="columns")

	# filter ordination df by abundance
	ordination_filtered_df = filter_by_abundance(
		df=ordination_collapsed_df.drop(['Taxon'], axis="columns"),
		abundance_threshold=abundance_threshold,
		percent_axis=0,
		filter_axis=1
	)

	# transpose feature table so that it has samples as rows, taxa/ASV as columns
	ordination_transposed_df = ordination_filtered_df.T
	abundance_transposed_df = abundance_collapsed_df_reindexed.T

	# Remove samples that have total counts <= 5 (R complains if total count <= 5)
	count_filtered_df = filter_by_total_count(ordination_transposed_df)

	# Find sample intersection of feature table, sample metadata, and environmental metadata
	intersection_feature_table_df, intersection_abundance_df, intersection_sample_metadata_df, intersection_environmental_metadata_df = find_sample_intersection(
		count_filtered_df,
		abundance_transposed_df,
		sample_metadata_df,
		env_metadata_df
	)

	r_feature_table = convert_pd_df_to_r(intersection_feature_table_df)
	r_abundance_table = convert_pd_df_to_r(intersection_abundance_df)

	r_dissimilarity_matrix = calculate_dissimilarity_matrix(r_feature_table, method=dissmilarity_index)

	ordination = calculate_ordination(r_dissimilarity_matrix)

	wascores = calculate_weighted_average(ordination, r_abundance_table)

	r_env_metadata = convert_pd_df_to_r(intersection_environmental_metadata_df)
	projection = project_env_metadata_to_ordination(ordination, r_env_metadata, PC_axis_one, PC_axis_two)

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
	renamed_vector_arrow_df = rename_as_PC_columns(vector_arrow_df, PC_axis_one, PC_axis_two)

	# Add normalized taxa count and filter by user specifed thresehold
	normalized_wascores_df = normalized_taxa_total_abundance(renamed_wascores_df, intersection_abundance_df)
	filtered_wascores_df = filter_by_wascore_threshold(normalized_wascores_df, wa_threshold)

	# Proportion explained
	proportion_explained = get_variance_explained(ordination_eig_df)

	# Combine ordination df and sample metadata df
	merged_df = renamed_ordination_point_df.join(intersection_sample_metadata_df, how="inner")

	return merged_df, renamed_vector_arrow_df, filtered_wascores_df, proportion_explained

def make_triplot(merged_df, vector_arrow_df, wascores_df, proportion_explained,
	fill_variable, PC_axis_one=1, PC_axis_two=2, alpha=0.9, stroke=0.6,
	point_size=6, x_axis_text_size=10, y_axis_text_size=10, legend_title_size=10,
	legend_text_size=10):
	"""

	"""
	# raise AXIOME3Error if PC_axis1 == PC_axis2
	if(PC_axis_one == PC_axis_two):
		raise AXIOME3Error("PC axis one and PC axis two cannot be equal!")

	# Remove unused categories
	merged_df[fill_variable] = merged_df[fill_variable].cat.remove_unused_categories()

	# PC axes to visualize
	pc1 = 'PC'+str(PC_axis_one)
	pc2 = 'PC'+str(PC_axis_two)

	# Plot the data
	base_plot = ggplot(
		merged_df, 
		aes(
			x=pc1,
			y=pc2,
			label=merged_df.index,
			fill=fill_variable
		)
	)
	base_points = geom_point(size=point_size, alpha=alpha, stroke=stroke)

	base_anno = geom_text(size=4)

	PC_axis_one_variance = str(round(proportion_explained.loc[pc1, 'proportion_explained'],2))
	PC_axis_two_variance = str(round(proportion_explained.loc[pc2, 'proportion_explained'],2))
	x_label_placeholder = pc1 + "(" + PC_axis_one_variance + "%)"
	y_label_placeholder = pc2 + "(" + PC_axis_two_variance + "%)"
	x_lab = xlab(x_label_placeholder)
	y_lab = ylab(y_label_placeholder)

	my_themes = theme(
		panel_grid=element_blank(), # No grid
		panel_border=element_rect(colour='black'), # black outline
		legend_key=element_blank(), # No legend background
		axis_title_x=element_text(size=x_axis_text_size), # x axis label size
		axis_title_y=element_text(size=y_axis_text_size), # y axis label size
		legend_title=element_text(size=legend_title_size, face='bold'), # legend titel size
		legend_text=element_text(size=legend_text_size), # legend text size
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
				x=pc1,
				y=pc2,
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
				x=pc1,
				y=pc2,
				label=wascores_df.index
			),
			data=wascores_df,
			inherit_aes=False,
			size=4
		)

		if(point_size <= 5):
			taxa_max_size = point_size * 4
		elif(point_size <= 10):
			taxa_max_size = point_size * 3
		else:
			taxa_max_size = point_size * 1.5
		plot = plot + taxa_points + scale_size_area(max_size=taxa_max_size) + taxa_anno

	# if vector arrows pass the thresohld
	if(vector_arrow_df.shape[0] > 0):
		env_arrow = geom_segment(
			aes(
				x=0,
				xend=pc1,
				y=0,
				yend=pc2,
				colour=vector_arrow_df.index
			),
			data=vector_arrow_df,
			arrow=arrow(length=0.1),
			inherit_aes=False,
			show_legend=False
		)

		env_anno = geom_text(
			aes(
				x=pc1,
				y=pc2,
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
#	ordination_collapse_level="asv",
#	wascores_collapse_level="phylum",
#	abundance_threshold=0.05,
#	wa_threshold=0.01,
#	R2_threshold=0.15,
#	PC_axis_one=1,
#	PC_axis_two=2
#)
#triplot = make_triplot(
#	merged_df,
#	vector_arrow_df,
#	wascores_df,
#	proportion_explained,
#	fill_variable="I5_Index_ID",
#	PC_axis_one=1,
#	PC_axis_two=2
#)
#save_plot(triplot, "plot")


#feature_table_artifact_path = "/pipeline/AXIOME3/scripts/qiime2_helper/qiime2_2020_6_analysis_output/dada2/merged/merged_table.qza"
#taxonomy_artifact_path = "/pipeline/AXIOME3/scripts/qiime2_helper/qiime2_2020_6_analysis_output/taxonomy/taxonomy.qza"