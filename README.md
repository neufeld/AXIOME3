# AXIOME3 (16S rRNA analysis pipeline)

## About
16S rRNA analysis workflow based on QIIME2 wrapped in luigi framework.

Currently, it uses conda 4.7.12 and QIIME2 version 2019-10.

Be aware that this repository is going through rapid changes in case you plan to actively make use of this project.

**Note that previous versions of conda may cause problems.**

## Required packages
**conda 4.7.12 or newer** (No guarantee previous versions of conda will work!)  
**QIIME2 (tested with 2019-04, 2019-07, 2019-10)**

Refer to `conda_env_file/qiime2-2019.10_AXIOME3.yml` file for details.

## Setting up conda environment for AXIOME3 (only has to be done once)

1. Clone this repository to your home directory.

```
cd ~
git clone https://github.com/neufeld/AXIOME3.git
```

2. Change directory to AXIOME3.

```
cd AXIOME3
```

3. Install conda environment directly from .yml file in this repository.

```
conda env create --name <ENV_NAME> --file conda_env_file/qiime2-2019.10_AXIOME3.yml
```

*Make sure to replace <ENV_NAME> with actual name*  
*Try to give meaningful names such as AXIOME3_2019.10 so that you can easily switch between environments with different AXIOME3 versions*

```
e.g.
conda env create --name AXIOME3_2019.10 --file conda_env_file/qiime2-2019.10_AXIOME3.yml
```
	
4. Activate your AXIOME3 environment (if you already activated, ignore this step).

```
conda activate <AXIOME3_ENV>

(Replace <AXIOME3_ENV> with the environment name you chose)
``` 

## Updating existing AXIOME3 environment to latest version
1. Update the local repository by running the command

```
git pull
```

*This command will download the latest updates to your local computers*

2. Activate existing AXIOME3 environment

```
conda activate <AXIOME3_ENV>
```

*replace <AXIOME3_ENV> with actual name*

3. Update the environment from .yml file

```
conda env update --file conda_env_file/qiime2-2019.10_AXIOME3.yml
```

## Usage

### Generating Manifest file

There is a script that can make a manifest file given  
a. SampleSheet (used for MiSeq), and  
b. the directory that has sequence data (fastq.gz files) (this will be the directory that stores MiSeq data)

_You don't have to do this if you already have a manifest file_

_Skip to Running Pipeline Section if you already have a manifest file_

You can use the script by running the command  
```
- General Format -
python scripts/generate_manifest.py \
	--samplesheet <PATH TO SAMPLESHEET USED IN MISEQ> # It should ONLY have your samples \
	--data-dir <PATH TO DIRECTORY THAT HAS SEQUENCE FILES>
-------------------------------------------------
- Actual Example -
python scripts/generate_manifest.py \
	--samplesheet ~/manifest_test/SampleSheetCorrected160713.csv \
	--data-dir  ~/manifest_test
```

#### VERY IMPORTANT

**Samplesheet should only have your samples. If your samplesheet has samples owned by multiple people (i.e. you ran MiSeq with other people), you MUST change the original samplesheet so that it will only have your samples**

For example, in the following samplesheet,

```
Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description
DD11,11,nested,A11,V4-R9,GATCAG,Pro341Fi4,AAGGCC,,
DD12,12,1,A12,V4-R17,TCCTCA,Pro341Fi4,AAGGCC,,
DD13,13,1,B1,V4-R2,CGATGT,Pro341Fi1,TCTCGG,,
DD14,14,1,B2,V4-R10,TAGCTT,Pro341Fi1,TCTCGG,,
DD15,15,1,B3,V4-R18,GGTTGT,Pro341Fi1,TCTCGG,,
```

If DD11 and DD12 are not your samples, remove these two lines from the samplesheet like so.

```
Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description
DD13,13,1,B1,V4-R2,CGATGT,Pro341Fi1,TCTCGG,,
DD14,14,1,B2,V4-R10,TAGCTT,Pro341Fi1,TCTCGG,,
DD15,15,1,B3,V4-R18,GGTTGT,Pro341Fi1,TCTCGG,,
```

### Running Pipeline

It can handle multiple Illumina runs from different timestamps. All you have to do is adding "run_ID" column (case sensitive) to the manifest file as shown below. (run_ID does not necessarily have to be numbers)

```
sample-id,absolute-filepath,direction,run_ID
RBH08,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/41_S41_L001_R1_001.fastq.gz,forward,1
RBH08,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/41_S41_L001_R2_001.fastq.gz,reverse,1
RBH09,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/42_S42_L001_R1_001.fastq.gz,forward,1
RBH09,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/42_S42_L001_R2_001.fastq.gz,reverse,1
RBH12,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/45_S45_L001_R1_001.fastq.gz,forward,2
RBH12,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/45_S45_L001_R2_001.fastq.gz,reverse,2
RBH13,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/46_S46_L001_R1_001.fastq.gz,forward,2
RBH13,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/46_S46_L001_R2_001.fastq.gz,reverse,2
```

**If "run_ID" column is NOT present in the manifest file, the pipeline will assume all the samples come from the same run**

## Core Analysis

This section covers core part of 16S rRNA analysis workflow that most people would want to run. 

0. Activate AXIOME3 conda environment and cd to AXIOME3 (if you haven't already done so).

1. Generate configuration file by running luigi_config_generator.py.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--sample-type <SAMPLE_TYPE [default = SampleData[PairedEndSequencesWithQuality]]> \
	--input-format <INPUT_FORMAT [default = PairedEndFastqManifestPhred33]>
-----------------------------------------------------------------------------
- Actual Example -

python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--sample-type SampleData[PairedEndSequencesWithQuality] \
	--input-format PairedEndFastqManifestPhred33
```

You may refer to `https://docs.qiime2.org/2019.10/tutorials/importing/` (open the document from latest version) for more information regarding `sample-type` and `input-format`.

At the Neufeld Lab, `sample-type` will often be `SampleData[PairedEndSequencesWithQuality]`, and `input-format` is either `PairedEndFastqManifestPhred33` or `PairedEndFastqManifestPhred33V2` depending on the format of manifest file you are using.

*(Manifest file can be in either CSV or TSV formats)*

**Example of PairedEndFastqManifestPhred33 manifest file**
```
sample-id,absolute-filepath,direction
RBH08,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/41_S41_L001_R1_001.fastq.gz,forward
RBH08,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/41_S41_L001_R2_001.fastq.gz,reverse
RBH09,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/42_S42_L001_R1_001.fastq.gz,forward
RBH09,/Data/Katja/Illumina_MiSeq_data/180924_NWMO/42_S42_L001_R2_001.fastq.gz,reverse
```

**Example of PairedEndFastqManifestPhred33V2 manifest file**
```
sample-id     forward-absolute-filepath       reverse-absolute-filepath
sample-1      $PWD/some/filepath/sample0_R1.fastq.gz  $PWD/some/filepath/sample1_R2.fastq.gz
sample-2      $PWD/some/filepath/sample2_R1.fastq.gz  $PWD/some/filepath/sample2_R2.fastq.gz
sample-3      $PWD/some/filepath/sample3_R1.fastq.gz  $PWD/some/filepath/sample3_R2.fastq.gz
sample-4      $PWD/some/filepath/sample4_R1.fastq.gz  $PWD/some/filepath/sample4_R2.fastq.gz
```

**Note that *you don't have to* specify `--sample-type` and `--input-format` if you're okay with the default values.** 
If this is the case, simply run

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE>
-----------------------------------------------------------------------------
- Actual Example -

python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt
```

2. Run luigi pipeline to generate summary file for you to examine it.

```
python 16S_pipeline.py Summarize --local-scheduler
```

When it's done running you should see something like this (takes some time to run)

```
===== Luigi Execution Summary =====

Scheduled 2 tasks of which:
* 2 ran successfully:
    - 1 Import_Data(sample_type=SampleData[PairedEndSequencesWithQuality], input_format=PairedEndFastqManifestPhred33)
    - 1 Summarize()

This progress looks :) because there were no failed tasks or missing dependencies

===== Luigi Execution Summary =====
```

Examine your working directory. You will see a new directory called "output".

```
output/
├── paired-end-demux.qza
└── paired-end-demux.qzv
```

You may examine "paired-end-demux.qzv" file using QIIME2 View (https://view.qiime2.org/) to determine trim and truncation cutoff (to denoise reads).  
(Upload paired-end-demux.qzv file in QIIME2 View, and click on "Interactive Quality Plot" tab)

There are maximum values for cutoff values for **trunc-len-f and trunc-len-r** if you wish to maintain an overlapping region. (See the diagram below for visual explanation)

**Note that the illustrated amplicon is specific to the Neufeld Lab. Maximum cutoff values may differ if using different amplicons and/or sequencing technology**

![alt text](https://github.com/neufeld/AXIOME3/blob/master/img/amplicon.jpeg "DADA2 Amplicon Cutoff Reference")

3. After determining denoise cutoff values, generate configuration file again to specify cutoff values.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--trim-left-f <TRIM_LEFT_F_VALUE [default = 19]> \
	--trunc-len-f <TRUNC_LEN_F_VALUE [default = 250]> \
	--trim-left-r <TRIM_LEFT_R_VALUE [default = 20]> \
	--trunc-len-r <TRUNC_LEN_R_VALUE [default = 250]>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--trim-left-f 19 \
	--trunc-len-f 250 \
	--trim-left-r 20 \
	--trunc-len-r 250
```

_(Again) Note that if you are okay with the default values, you can run the command below instead._

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE>
-----------------------------------------------------------------------------
- Actual Example -

python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt
```

**_It is important that the classifier version MATCHES the qiime 2 version. It will throw an error otherwise_**

4. Run the pipeline to denoise your reads. This step acts as the 2nd checkpoint since denoising takes the most amount of time during 16S rRNA analysis. (could take 10~50min depending on the number of samples)


`python 16S_pipeline.py Merge_Denoise --local-scheduler`


When it's done running, your output directory will look something like this.  


```
output/dada2/
├── dada2_log.txt
├── dada2_rep_seqs.qza
├── dada2_table.qza
├── merged
│   ├── merged_rep_seqs.qza
│   └── merged_table.qza
├── stats_dada2.qza
```

You may examine 'sample_counts.tsv' file to determine sub-sampling depth value for the post analysis steps (e.g. rarefaction, distance metrics, PCoA, alpha significance groups)

**_Note that 'merged_table.qza' will be identical to 'dada2_table.qza' if all your samples are from SINGLE Illumina run._**

5. Generate configuration file again (to finish the rest of the workflow).

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--classifier <PATH_TO_YOUR_CLASSIFIER_FILE [default = qiime2-2019-07 version]>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--classifier /Data/reference_databases/qiime2/training_classifier/silva132_V4V5_qiime2-2019.7/classifier_silva_132_V4V5.qza
```

_(Again) Note that if you are okay with default values, you can run the command below instead._

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE>
-----------------------------------------------------------------------------
- Actual Example -

python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt
```

**_It is important that the classifier version MATCHES the qiime 2 version. It will throw an error otherwise_**

6. Run luigi pipeline to run the rest of the worflow.

```
python 16S_pipeline.py Core_Analysis --local-scheduler
```

When it's done running, your screen should look something like this

```
===== Luigi Execution Summary =====

Scheduled 14 tasks of which:
* 9 complete ones were encountered:
    - 1 Convert_Biom_to_TSV()
    - 1 Denoise_Tabulate()
    - 1 Export_Representative_Seqs()
    - 1 Export_Taxonomy()
    - 1 Merge_Denoise()
    ...
* 5 ran successfully:
    - 1 Convert_Rarefy_Biom_to_TSV()
    - 1 Core_Analysis()
    - 1 Export_Rarefy_Feature_Table()
    - 1 Generate_Combined_Feature_Table()
    - 1 Rarefy(sampling_depth=10000)

This progress looks :) because there were no failed tasks or missing dependencies

===== Luigi Execution Summary =====
```

7. Your "output" directory (directory named "output") should look something like this

```
output/
├── core_analysis_done
├── dada2
│   ├── dada2_log.txt
│   ├── dada2_rep_seqs.qza
│   ├── dada2_table.qza
│   ├── merged
│   │   ├── merged_dada2_rep_seqs.qzv
│   │   ├── merged_rep_seqs.qza
│   │   └── merged_table.qza
│   ├── sample_counts.tsv
│   ├── stats_dada2.qza
│   └── stats_dada2.qzv
├── exported
│   ├── ASV_abundance_filtered.tsv
│   ├── ASV_table_combined.log
│   ├── ASV_table_combined.tsv
│   ├── dna-sequences.fasta
│   ├── feature-table.biom
│   ├── feature-table.tsv
│   └── taxonomy.tsv
├── manifest
│   └── manifest.csv
├── paired_end_demux.qzv
├── pcoa_plots
│   ├── bray_curtis_pcoa_plots.pdf
│   ├── jaccard_pcoa_plots.pdf
│   ├── unweighted_unifrac_pcoa_plots.pdf
│   └── weighted_unifrac_pcoa_plots.pdf
├── phylogeny
│   ├── aligned_rep_seqs.qza
│   ├── masked_aligned_rep_seqs.qza
│   ├── rooted_tree.qza
│   └── unrooted_tree.qza
├── taxa_collapse
│   ├── class_collapsed_table.qza
│   ├── class_collapsed_table.tsv
│   ├── domain_collapsed_table.qza
│   ├── domain_collapsed_table.tsv
│   ├── family_collapsed_table.qza
│   ├── family_collapsed_table.tsv
│   ├── genus_collapsed_table.qza
│   ├── genus_collapsed_table.tsv
│   ├── order_collapsed_table.qza
│   ├── order_collapsed_table.tsv
│   ├── phylum_collapsed_table.qza
│   ├── phylum_collapsed_table.tsv
│   ├── species_collapsed_table.qza
│   └── species_collapsed_table.tsv
├── taxonomy
│   ├── taxonomy_log.txt
│   ├── taxonomy.qza
│   └── taxonomy.qzv
└── version_info.txt

```

_if you don't see the above message (notice the smiley face, ":)"), or your output directory is missing some files, it means the pipeline is not successfully run. Check with the lab's bioinformatician if the error is not obvious_

## Post Analysis
This section is the extension of "Core Analysis" section. **It requires all the outputs from the "Core Analysis" section, so DO NOT remove any files or folders if you wish to run this section.**  

**You can also re-run post analysis if wanting to try different sampling depths or metadata file. In this case,** 
1. Remove/rename/move output/post_analysis directory.
2. Prepare a metadata file with subset of the samples listed. (if wanting to re-run the analysis with the subset of the samples)

**A lot of the steps in post analysis are dependent on sampling depth parameter. Any samples that are below the sampling depth parameter will be thrown away.**

*You may examine output/post_analysis/filtered/filtered_table_summary.txt file to determine appropriate sampling depth for your samples. Usually, picking the lowest value possible that does not vary as much between samples works well*

### - Core Metrics Phylogeny -
It generates PCoA plots based on various distance metrics (Jaccard, Bray-Curtis, Weighted/Unweighted Unifrac), and all the intermediate outputs.

**Note: It will filter the samples first by sampling depth threshold, then by the samples listed in your metadata file. (For example, it will first remove samples that do NOT meet sampling depth threshold, then furthur remove samples that are not present in the metadata file)**

1. Generate configuration file.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--metadata <PATH_TO_YOUR_METADATA_FILE> \
	--sampling-depth <SAMPLING_DEPTH_FOR_RAREFACTION [DEFAULT = 1,000]>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--metadata /Winnebago/danielm710/input/sample-metadata.tsv \
	--sampling-depth 1000
```

2. Run the pipeline 

```
python 16S_pipeline.py Core_Metrics_Phylogeny --local-scheduler
```

This should create `core_div_phylogeny` directory with its respective outputs.

### - Rarefaction -
This step will rarefy feature table generated using DADA2 to a user specified sampling depth (or 1,000 if sampling depth not specified), and generate combined ASV table with the rarefied feature table.

1. Generate configuration file.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--metadata <PATH_TO_YOUR_METADATA_FILE> \
	--sampling-depth <SAMPLING_DEPTH_FOR_RAREFACTION [DEFAULT = 1,000]>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--metadata /Winnebago/danielm710/input/sample-metadata.tsv \
	--sampling-depth 1000
```

2. Run the pipeline 

```
python 16S_pipeline.py Generate_Combined_Rarefied_Feature_Table --local-scheduler
```

This should generate `rarefy_exported` and `rarefy` directories with their respective outputs.

### - Alpha Group Significance -
This step can be used to explore the relationship between alpha diversity and the user provided metadata. (Output will be QIIME2 Zipped View (.qzv)). You may go to `https://view.qiime2.org/` to examine this file

1. Generate configuration file.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--metadata <PATH_TO_YOUR_METADATA_FILE> \
	--sampling-depth <SAMPLING_DEPTH_FOR_RAREFACTION [DEFAULT = 1,000]>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--metadata /Winnebago/danielm710/input/sample-metadata.tsv \
	--sampling-depth 1000
```

2. Run the pipeline 

```
python 16S_pipeline.py Alpha_Group_Significance --local-scheduler
```

This should generate `alpha_group_significance` directory with its respective outputs.

### - 2D PCoA Plots -
This step will generate multiple 2D PCoA plots, each of which corresponds to a column in the user provided metadata file, for multiple distance metrics (unweighted/weighted unifrac, bray-curtis, jaccard) in a PDF format.

1. Generate configuration file.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--metadata <PATH_TO_YOUR_METADATA_FILE> \
	--sampling-depth <SAMPLING_DEPTH_FOR_RAREFACTION [DEFAULT = 1,000]>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--metadata /Winnebago/danielm710/input/sample-metadata.tsv \
	--sampling-depth 1000
```

2. Run the pipeline 

```
python 16S_pipeline.py PCoA_Plots --local-scheduler
```

This should generate `pcoa_plots` directory with its respective outputs.

3. Note that this output may not necessarilly be "publication quality" plot. You may run a separate script to make a nicer quality PCoA plot. Refer to [generate_pcoa.py guideline](scripts/README.md) for more details.

### - Running all Post Analysis Steps -

Alternatively, you may run the commands below to generate all the outputs in the "Post Analysis" section.

1. Generate configuration file.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--metadata <PATH_TO_YOUR_METADATA_FILE> \
	--sampling-depth <SAMPLING_DEPTH_FOR_RAREFACTION [DEFAULT = 1,000]>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--metadata /Winnebago/danielm710/input/sample-metadata.tsv \
	--sampling-depth 1000
```

2. Run the pipeline 

```
python 16S_pipeline.py Post_Analysis --local-scheduler
```

This should create `rarefy_exported`, `rarefy`, `core_div_phylogeny` and `alpha_group_significance` directories with their respective outputs.

### Cleaning Up Working Directory

Make sure to rename or move 'output' directory to somewhere else when you are done running the pipeline.

**by default, luigi pipeline looks at "output" directory to check for successful tasks, so if all the files already exist in this directory (e.g. from analyzing your previous samples), it will think there aren't any jobs to be run for the new samples since all the files are there.**

##### Moving directory example
Let's say you want to move "output" directory to "Analysis" directory under the home directory, and rename it to "Illumina_Run3".

You may run the command below to do so.

`mv output ~/Analysis/Illumina_Run3` ("~" means home directory)
