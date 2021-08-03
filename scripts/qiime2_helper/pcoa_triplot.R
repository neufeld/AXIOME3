suppressMessages(library(vegan))
# Commandline arguments
args = commandArgs(trailingOnly=TRUE)

# first arg: abundance filtered taxa collapsed table
# second arg: metadata file
# third arg: environmental metadata file
# fourth arg: R2 value threshold
# fifth arg: output path
#if(length(args) < 5) {
#	stop("Not enough arguments supplied")
#}

feature_table_filepath = args[1]
taxa_filepath = args[2]
metadata_path = args[3]
env_filepath = args[4]
dissmilarity_index = args[5]
r2_threshold = as.numeric(args[6])
pval_threshold = as.numeric(args[7])
wa_threshold = as.numeric(args[8])
PC_axis_one = as.numeric(args[9])
PC_axis_two = as.numeric(args[10])
output_path = args[11]

#feature_table_filepath = "/pipeline/AXIOME3/scripts/qiime2_helper/feature_table.csv"
#taxa_filepath = "/pipeline/AXIOME3/scripts/qiime2_helper/abundance_df.csv"
#metadata_path = "/pipeline/AXIOME3/scripts/qiime2_helper/metadata_df.csv"
#env_filepath = "/pipeline/AXIOME3/scripts/qiime2_helper/env_metadata_df.csv"
#dissmilarity_index = "bray"
#r2_threshold = 0.1
#pval_threshold = 0.2
#wa_threshold = 0.1
#PC_axis_one = 1
#PC_axis_two = 2
#output_path = '.'

# inputs are preprocessed from Python
feature.table.df <- read.table(feature_table_filepath, header=TRUE, row.names=1, sep=',')
taxa.bubble.df <- read.table(taxa_filepath, header=TRUE, row.names=1, sep=',')
metadata.df <- read.table(metadata_path, header=TRUE, row.names=1, sep=',')
env.metadata.df <- read.table(env_filepath, header=TRUE, row.names=1, sep=',')

if(nrow(feature.table.df) == 0) {
	stop("feature table is empty or has no common samples with other inputs.")
}

if(nrow(taxa.bubble.df) == 0) {
	stop("taxonomy file is empty or has no common samples with other inputs.")
}

if(nrow(metadata.df) == 0) {
	stop("metadata file is empty or has no common samples with other inputs.")
}

if(nrow(env.metadata.df) == 0) {
	stop("environmental metadata file is empty or has no common samples with other inputs.")
}

# number of samples in the feature table
num.samples <- nrow(feature.table.df)

# Calculate dissmilarity matrix
dissmilarity.matrix <- vegdist(feature.table.df, method=dissmilarity_index)

# PCoA
# k is bounded by [1, max(num.samples-1, 10)]; less likely to visualize more than 10 PC axes
k <- min(10, num.samples-1)

# Raise error if specified PC axis is greater than num.samples
max.PC <- max(PC_axis_one, PC_axis_two)

if(max.PC > k) {
	message <- paste("Specified PC axis is greater than the maximum allowed value,", k)
	stop(message)
}

# Calculate PCoA using the dissmilarity matrix
pcoa <- cmdscale(dissmilarity.matrix, k=k, eig=TRUE)

# Weighted average of species
# It finds weighted average of PCoA coordinates with taxa abundance per sample as weights.
# In simple terms, it essentially finds contribution of each taxa to each coordinate.
wa <- wascores(pcoa$points[, 1:k], taxa.bubble.df)

# Project environmental data onto PCoA axis
proj.env <- suppressMessages(envfit(pcoa, env.metadata.df))

# Extract vector arrows, R2, and pvals
pvals <- proj.env$vectors$pvals
r2 <- proj.env$vectors$r
arrow <- proj.env$vectors$arrows
proj.env.matrix <- cbind(arrow, R2=r2, pvals=pvals)
proj.env.df <- as.data.frame(proj.env.matrix)
# Filter vector projection based on R2 value and pval
pval.filtered <- proj.env.df[, "pvals"] < pval_threshold
if(!any(pval.filtered)) {
	message <- paste("No samples remaining after filtering by specified p-value threshold,", pval_threshold)
	stop(message)
}

r2.filtered <- proj.env.df[, "R2"] > r2_threshold
if(!any(r2.filtered)) {
	message <- paste("No samples remaining after filtering by specified R2 threshold,", r2_threshold)
	stop(message)
}

filtered <- pval.filtered & r2.filtered
if(!any(filtered)) {
	stop("No samples remaining after filtering by specified p-value and R2 thresholds")
}

filtered.arrow.matrix <- proj.env.df[filtered, !colnames(proj.env.df) %in% c("pvals", "R2")]

# Make as dataframe
pcoa.df <- as.data.frame(pcoa$points)
wa.df <- as.data.frame(wa)
proj.arrow.df <- as.data.frame(filtered.arrow.matrix * sqrt(proj.env.df[r2.filtered, "R2"]))

# Rename columns
# For env metadata df (will only have two PC axis)
env.col.names <- paste("Axis ", c(PC_axis_one, PC_axis_two), sep="")
colnames(proj.arrow.df) <- env.col.names
# Everything else
num.cols <- 1:ncol(pcoa.df)
new.col.names <- paste("Axis ", num.cols, sep="")
colnames(pcoa.df) <- new.col.names
colnames(wa.df) <- new.col.names

# Calculate normalized, total abundance of each taxa
total_abundance <- sum(taxa.bubble.df)
taxa_count <- apply(taxa.bubble.df, 2, sum)
normalized_taxa_count <- taxa_count / total_abundance

# Append to wa.df
wa.df$abundance <- normalized_taxa_count

# Filter by weighted average threshold
filtered.wa.df <- wa.df[wa.df$abundance > wa_threshold,]

# Metadata file
#metadata_path <- "metadata_MaCoTe.tsv"
metadata <- read.table(metadata_path, header=TRUE, sep=",", row.names=1, comment.char="#")
metadata.df <- as.data.frame(metadata)

# Merge metadata with pcoa data
pcoa.df$SampleID <- rownames(pcoa.df)
metadata.df$SampleID <- rownames(metadata.df)
merged.df <- merge(pcoa.df, metadata.df, by="SampleID") 
rownames(merged.df) <- merged.df$SampleID

# Calculate proportion explained
total_variance <- sum(pcoa$eig)
proportion_explained <- (pcoa$eig / total_variance) * 100
proportion.df <- as.data.frame(proportion_explained)
colnames(proportion.df) <- 'proportion_explained'
new.prop.rownames <- paste('Axis ', 1:nrow(proportion.df), sep='')
rownames(proportion.df) <- new.prop.rownames

# save intermediate outputs as csv (or tsv)\
# prior to saving, make SampleID column

# merged.df proj.arrow.df filtered.wa.df proj.env.df proportion.df
merged.df.path <- file.path(output_path, "processed_merged_df.csv")
proj.arrow.df.path <- file.path(output_path, "processed_vector_arrow_df.csv")
filtered.wa.df.path <- file.path(output_path, "processed_wa_df.csv")
proj.env.df.path <- file.path(output_path, "processed_projection_df.csv")
proportion.df.path <- file.path(output_path, "processed_proportion_explained_df.csv")

write.table(merged.df, merged.df.path, quote=FALSE, sep=",", row.names=FALSE)
write.table(proj.arrow.df, proj.arrow.df.path, quote=FALSE, sep=",", row.names=TRUE)
write.table(filtered.wa.df, filtered.wa.df.path, quote=FALSE, sep=",", row.names=TRUE)
write.table(proj.env.df, proj.env.df.path, quote=FALSE, sep=",", row.names=TRUE)
write.table(proportion.df, proportion.df.path, quote=FALSE, sep=",", row.names=TRUE)

paths <- paste(c(merged.df.path, proj.arrow.df.path, filtered.wa.df.path, proj.env.df.path, proportion.df.path), sep=";")

print(wa_threshold)