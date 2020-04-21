library(vegan)
library(ggplot2)
# Commandline arguments
args = commandArgs(trailingOnly=TRUE)

# first arg: abundance filtered taxa collapsed table
# second arg: metadata file
# third arg: environmental metadata file
# fourth arg: R2 value threshold
# fifth arg: output path
if(length(args) < 5) {
	stop("Not enough arguments supplied")
}

taxa_filepath = args[1]
metadata_path = args[2]
env_filepath = args[3]
r2_threshold = args[4]
output_path = args[5]

# Collapsed taxa table
#taxa_filepath <- "20p_genus_collapsed.tsv"
taxa.df <- read.table(taxa_filepath, header=TRUE, row.names=1, sep="\t")
# Remove rows with rowSums less than or equal to 5
to.remove.idx <- rowSums(taxa.df) <= 5
to.remove.samples <- rownames(taxa.df)[to.remove.idx]
#taxa.df <- taxa.df[!to.remove.idx, ]
taxa.df <- subset(taxa.df, !to.remove.idx)
msg <- c("Following samples were removed from the feature table because their row sum <= 5:", to.remove.samples)
warning(paste(msg, collapse=' '))

# Load environment variables (using fake data for now)
#env_filepath = "environmental_metadata.tsv"
env.df <- read.table(env_filepath, header=TRUE, sep="\t", row.names=1)

# Only retain samples that are found in both taxa and environmental metadata
intersect.rownames <- intersect(rownames(env.df), rownames(taxa.df))
env <- subset(env.df, rownames(env.df) %in% intersect.rownames)
taxa <- subset(taxa.df, rownames(taxa.df) %in% intersect.rownames)

env.missing <- rownames(env.df)[!rownames(env.df) %in% intersect.rownames]
taxa.missing <- rownames(taxa.df)[!rownames(taxa.df) %in% intersect.rownames]
env.missing.msg <- c("Following samples are dropped from the environment metadata because they could not be found in the feature table:", env.missing)
taxa.missing.msg <- c("Following samples are dropped from the feature table because they could not be found in the environmenta metadata:", taxa.missing)
warning(paste(env.missing.msg, collapse=' '))
warning(paste(taxa.missing.msg, collapse=' '))

# Create an empty file if empty feature table
if(nrow(taxa) == 0 | ncol(taxa) == 0) {
	warning("Feature Table empty after dropping samples... Craeting an empty file")
	file.create(output_path)
}

# Calculate bray curtis distance
taxa.bray <- vegdist(taxa)

# PCoA
taxa.bray.pcoa <- cmdscale(taxa.bray, k=3, eig=TRUE)

# Weighted average of species
# It finds weighted average of PCoA coordinates with taxa abundance per sample as weights.
# In simple terms, it essentially finds contribution of each taxa to each coordinate.
taxa.wa <- wascores(taxa.bray.pcoa$points[, 1:3], taxa)

# TODO: If rows are missing, throw error

# Project environmental data onto PCoA axis
taxa.bray.pcoa.env <- envfit(taxa.bray.pcoa, env)

# Make as dataframe
taxa.bray.pcoa.df <- as.data.frame(taxa.bray.pcoa$points)
taxa.wa.df <- as.data.frame(taxa.wa)
taxa.bray.pcoa.env.df <- as.data.frame(taxa.bray.pcoa.env$vectors$arrows * sqrt(taxa.bray.pcoa.env$vectors$r))
# Filter based on R2 value
r.sqr.filtered <- names(taxa.bray.pcoa.env$vectors$r[taxa.bray.pcoa.env$vectors$r > r2_threshold])
taxa.bray.pcoa.env.df <- subset(taxa.bray.pcoa.env.df, rownames(taxa.bray.pcoa.env.df) %in% r.sqr.filtered)
should.include <- nrow(taxa.bray.pcoa.env.df) > 0

# Rename columns
colnames(taxa.bray.pcoa.df) <- c("PC1", "PC2", "PC3")
colnames(taxa.wa.df) <- c("PC1", "PC2", "PC3")
colnames(taxa.bray.pcoa.env.df) <- c("PC1", "PC2")

# Add additional columns for ggplot
taxa.bray.pcoa.env.df$env_names <- rownames(taxa.bray.pcoa.env.df)
taxa.bray.pcoa.df$ID <- rownames(taxa.bray.pcoa.df)

# Metadata file
#metadata_path <- "metadata_MaCoTe.tsv"
metadata <- read.table(metadata_path, header=TRUE, sep="\t", row.names=1, comment.char="#")
metadata.df <- as.data.frame(metadata)
metadata.df$ID <- rownames(metadata.df)

# Merge metadata with pcoa data
merged.pcoa.df <- merge(taxa.bray.pcoa.df, metadata.df, by="ID") 
rownames(merged.pcoa.df) <- rownames(taxa.bray.pcoa.df)

# Make fill column category
merged.pcoa.df$NTCGroup <- as.factor(merged.pcoa.df$NTCGroup)

# Calculate normalized, total abundance of each taxa
total_abundance <- sum(taxa)
taxa_count <- apply(taxa, 2, sum)
normalized_taxa_count <- taxa_count / total_abundance

# Append to taxa.wa.df
taxa.wa.df$abundance <- normalized_taxa_count

# Calculate proportion explained
total_variance <- sum(taxa.bray.pcoa$eig)
proportion_explained <- taxa.bray.pcoa$eig / total_variance

# Convert to percent
proportion_explained <- proportion_explained * 100
proportion_explained <- round(proportion_explained, digits=2)
proportion_explained <- sapply(proportion_explained, function(x) {paste(c(x, '%'), collapse='')})

# Plot the data
base_plot = ggplot(merged.pcoa.df, 
		   aes(PC1, PC2,
		       fill=NTCGroup,
		       label=rownames(merged.pcoa.df)))

base_points = geom_point(size=5, shape=21)

base_anno = geom_text(size=4, point.padding=0.2)

# Taxa points
taxa_points = geom_point(aes(PC1, PC2, size=abundance),
			 data=taxa.wa.df,
			 inherit.aes=FALSE,
			 shape=21,
			 fill=NA,
			 show.legend=FALSE)

# Taxa annotation
taxa_anno = geom_text(aes(PC1, PC2,
			  label=rownames(taxa.wa.df)
			  ),
		      data=taxa.wa.df,
		      inherit.aes=FALSE,
		      size=4,
		      nudge_y=0.02)

# Add environmental data
if(should.include == TRUE) {
	env_arrow = geom_segment(aes(x=0, xend=PC1, y=0, yend=PC2),
				 data=taxa.bray.pcoa.env.df,
				 arrow = arrow(length = unit(0.5, "cm")),
				 colour="red",
				 inherit.aes=FALSE)

	env_anno = geom_text(aes(PC1, PC2, label=env_names),
				  data=taxa.bray.pcoa.env.df,
				  inherit.aes=FALSE,
				  colour="red",
				  nudge_y=-0.08,
				  nudge_x=-0.02)
}

my_themes = theme(
	      panel.grid=element_blank(), # No grid
	      panel.border=element_rect(fill=NA), # black outline
	      panel.background=element_rect(fill='white', colour='grey50'), # white background
	      legend.key=element_blank() # No legend background
	    )

x_label_placeholder <- paste("PC1 (",  proportion_explained[1], ")", sep="")
y_label_placeholder <- paste("PC2 (",  proportion_explained[2], ")", sep="")

x_lab <- xlab(x_label_placeholder)
y_lab <- ylab(y_label_placeholder)

full_plot = base_plot +
		base_points +
		taxa_points + scale_size_area(max_size=10) +
		x_lab +
		y_lab +
		my_themes +
		base_anno +
		taxa_anno

if(should.include == TRUE) {
	full_plot = full_plot + env_arrow + env_anno
}

pdf(output_path)
groups <- c("NTCGroup", "Types")
for (group in groups) {
	base_plot = ggplot(merged.pcoa.df, 
			   aes(PC1, PC2,
			       fill=get(group),
			       label=rownames(merged.pcoa.df)))

	full_plot = base_plot +
			base_points +
			taxa_points + scale_size_area(max_size=10) +
			x_lab +
			y_lab +
			my_themes +
			base_anno +
			taxa_anno +
			scale_fill_discrete(name=group)

	if(should.include == TRUE) {
		full_plot = full_plot + env_arrow + env_anno
	}
	print(full_plot)
}
dev.off()

#ggsave("plot.pdf", full_plot)
