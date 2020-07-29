from plotnine.scales import (
	scale_fill_brewer,
	scale_fill_continuous,
	scale_fill_discrete
)

# Custom exception
from exceptions.exception import AXIOME3Error

# Add a custom colour scale onto a plotnine ggplot
def add_fill_colours_from_users(plot, name, palette='Paired', brewer_type='qual'):
	try:
		custom_fill_brewer = scale_fill_brewer(type=brewer_type, palette=palette, name=name)
	except KeyError:
		raise AXIOME3Error(
			"Specified palette, '{palette}', and/or brewer type, '{brewer}', is not supported!".format(
				palette=palette,
				brewer=brewer_type
			)
		)
	plot = plot + custom_fill_brewer

	return plot

# Use this if more than 12 classes (colour brewer supports up to and including 12 classes)
def add_fill_colours_continous(plot, name):
	custom_fill_scale = scale_fill_continuous(name=name)

	plot = plot + custom_fill_scale

	return plot

def add_fill_colours_discrete(plot, name):
	custom_fill_scale = scale_fill_discrete(name=name)

	plot = plot + custom_fill_scale

	return plot