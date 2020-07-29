from rpy2.robjects.packages import importr
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter

VEGDIST_OPTIONS = {
	"Manhattan": "manhattan",
	"Euclidean": "euclidean",
	"Canberra": "canberra",
	"Bray-Curtis": "bray",
	"Kulczynski": "kulczynski",
	"Jaccard": "jaccard",
	"Gower": "gower",
	"altGower": "altGower",
	"Morisita": "morisita",
	"Horn-Morisita": "horn",
	"Chao": "chao",
	"Cao": "cao",
	"Mahalanobis":"mahalanobis"
}

def convert_pd_df_to_r(pd_df):
	with localconverter(ro.default_converter + pandas2ri.converter):
		r_df = ro.conversion.py2rpy(pd_df)

	return r_df

def convert_r_matrix_to_r_df(r_matrix):
	base = importr('base')

	r_df = base.as_data_frame(r_matrix)

	return r_df

def convert_r_df_to_pd_df(r_df):
	"""
	Convert R DataFrame to pandas DataFrame
	"""
	with localconverter(ro.default_converter + pandas2ri.converter):
		pd_df = ro.conversion.rpy2py(r_df)

	return pd_df