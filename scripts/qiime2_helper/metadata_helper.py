from qiime2 import (
	Artifact,
	Metadata
)

def load_metadata(metadata_path):
	# Use QIIME2 Metadata API to load metadata
	metadata_obj = Metadata.load(metadata_path)
	metadata_df = metadata_obj.to_dataframe()

	# Rename index
	metadata_df.index.names = ['SampleID']
	# By default, pandas treats string as object
	# Convert object dtype to category
	cols = metadata_df.columns
	object_type_cols = cols[metadata_df.dtypes == object]

	for col in object_type_cols:
		convert_col_dtype(metadata_df, col, "category")

	return metadata_df

def load_env_metadata(env_metadata_path):
	# Use QIIME2 Metadata API to load metadata
	env_metadata_obj = Metadata.load(env_metadata_path)
	env_metadata_df = env_metadata_obj.to_dataframe()

	# Rename index
	env_metadata_df.index.names = ['SampleID']
	# environmental metadata columns MUST be numeric type
	# Drop all non-numeric columns
	numeric_env_df = env_metadata_df.select_dtypes(include='number')

	if(len(numeric_env_df.columns) == 0):
		raise ValueError("Environmental metadata must contain at least one numeric column!")

	return numeric_env_df

def convert_col_dtype(df, col, dtype):
	"""
	Convert given column type to specified dtype
	"""
	if(col not in df.columns):
		raise ValueError("Column, {}, does not exist in the dataframe".format(col))

	df[col] = df[col].astype(dtype)

	return df

def check_column_exists(metadata_df, target_primary, target_secondary=None):
	"""
	Check if metadata has specified target columns
	"""
	# Make sure user specified target columns actually exist in the dataframe
	if(target_primary not in metadata_df.columns):
		msg = "Column '{column}' does NOT exist in the metadata!".format(
			column=target_primary
		)

		raise ValueError(msg)

	if(target_secondary is not None and
		target_secondary not in metadata_df.columns):
			msg = "Column '{column}' does NOT exist in the metadata!".format(
				column=target_secondary
			)

			raise ValueError(msg)