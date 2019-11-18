# Neufeld lab 16S RNA analysis pipeline

## About
16S RNA analysis workflow based on QIIME2 wrapped in luigi framework.

Currently, it uses conda 4.7.12 and QIIME2 version 2019-07.

Be aware that this repository is going through rapid changes if you plan to actively make use of this project.

**Note that previous versions of conda may cause problems.**

## Required packages
**conda 4.7.12 or newer** (No guarantee previous versions of conda will work!)  
**QIIME2 (tested with 2019-04 and 2019-07)**

Refer to 16S-luigi.yml file for details.

## Setting up conda virtual environment (only has to be done once)

1. Clone this repository to your home directory.

```
cd ~
git clone https://github.com/neufeld/AXIOME3.git
```

2. Change to AXIOME3

`cd AXIOME3`

### You don't have a qiime virtual environment yet OR You want to create a new conda environment for the pipeline

3.a. In this case, you can install conda environment directly from .yml file in this repository.

`conda env create --name <ENV_NAME> --file conda_env_file/AXIOME3.yml`

*Make sure to replace <ENV_NAME> with actual name*

e.g. `conda env create --name qiime_luigi --file conda_env_file/AXIOME3.yml`

Then, go to Step 4. (Activate your qiime2 environment)

### You already have an existing conda environment for qiime2 version 2019-07 AND don't mind updating the existing environment
<br />
3.b. In this case, you should just do...

##### i) activate your qiime environment 

`conda activate <YOUR_QIIME_ENV>`

##### ii) Make sure pip and python are pointing to anaconda packages **not to /usr/bin**

`which pip` should display something like `/Winnebago/danielm710/anaconda3/envs/qiime2-2019.7/bin/pip`

`which python` should display something like `/Winnebago/danielm710/anaconda3/envs/qiime2-2019.7/bin/python`

If you get something different (for example `/usr/local/bin/pip`, and `/usr/bin/python`), check if you have activated conda environment.

If you still get different messages, ask lab bioinformaticians for help.

##### iii) Install luigi by running the command...

`pip install luigi`

##### iv) Install BioPython and pandas (Jackson's script depends on these packages)

`conda install -c bioconda biopython pandas`
	
4. Activate your qiime2 environment (if you already activated, ignore this step).

`conda activate <QIIME_ENV>` (Replace <QIIME_ENV> with the environment name you chose)

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

#### Core Analysis

This section covers core part of 16S rRNA analysis workflow that most people would want to run. 

0. Activate conda environment and cd to Neufeld-16S-Pipeline (if you haven't already done so).

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

Note that *you don't have to* specify `--sample-type` and `--input-format` if you're okay with the default values.  
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

![alt text](https://github.com/neufeld/AXIOME3/blob/master/img/amplicon.jpeg "Amplicon DADA2 Cutoff Reference")

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

```
python 16S_pipeline.py Merge_Denoise --local-scheduler
```

When it's done running, your screen should look something like this (takes some time to run)

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
output
├── core_analysis_done
├── dada2
│   ├── dada2_log.txt
│   ├── dada2_rep_seqs.qza
│   ├── dada2_table.qza
│   ├── merged
│   │   ├── merged_dada2_rep_seqs.qzv
│   │   ├── merged_rep_seqs.qza
│   │   └── merged_table.qza
│   ├── stats_dada2.qza
│   └── stats_dada2.qzv
├── exported
│   ├── ASV_table_combined.log
│   ├── ASV_table_combined.tsv
│   ├── dna-sequences.fasta
│   ├── feature-table.biom
│   ├── feature-table.tsv
│   └── taxonomy.tsv
├── manifest
│   └── manifest.csv
├── paired_end_demux.qza
├── paired_end_demux.qzv
├── phylogeny
│   ├── aligned_rep_seqs.qza
│   ├── masked_aligned_rep_seqs.qza
│   ├── rooted_tree.qza
│   └── unrooted_tree.qza
├── rarefy
│   └── rarefied_table.qza
├── rarefy_exported
│   ├── ASV_rarefied_table_combined.log
│   ├── ASV_rarefied_table_combined.tsv
│   ├── feature-table.biom
│   └── feature-table.tsv
└── taxonomy
    ├── taxonomy_log.txt
    ├── taxonomy.qza
    └── taxonomy.qzv
```

_if you don't see the above message (notice the smiley face, ":)"), or your output directory is missing some files, it means the pipeline is not successfully run. Check with the lab's bioinformatician if the error is not obvious_

#### Post Analysis
This section is the extension of "Core Analysis" section. **It requires all the outputs from the "Core Analysis" section, so DO NOT remove any files or folders if you wish to run this section**

##### - Core Metrics Phylogeny -
It generates PCoA plots based on various distance metrics (Jaccard, Bray-Curtis, Weighted/Unweighted Unifrac), and all the intermediate outputs.

8. Generate configuration file.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--metadata <PATH_TO_YOUR_METADATA_FILE> \
	--sampling-depth <SAMPLING_DEPTH_FOR_RAREFACTION [DEFAULT = 10,000]>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--metadata /Winnebago/danielm710/input/sample-metadata.tsv \
	--sampling-depth 10000
```

9. Run the pipeline 

```
python 16S_pipeline.py Core_Metrics_Phylogeny --local-scheduler
```

**Note that you may repeat Step 8 and 9 to generate PCoA plots based on different rarefaction thresholds. Just make sure to remove "core_div_phylogeny" directory prior to do so**

`rm -r output/core_div_phylogeny`

10. Make sure to rename or move 'output' directory to somewhere else when you are done running the pipeline.

**by default, luigi pipeline looks at "output" directory to check for successful tasks, so if all the files already exist in this directory (e.g. from analyzing your previous samples), it will think there aren't any jobs to be run for the new samples since all the files are there.**

##### Moving directory example
Let's say you want to move "output" directory to "Analysis" directory under the home directory, and rename it to "Illumina_Run3".

You may run the command below to do so.

`mv output ~/Analysis/Illumina_Run3` ("~" means home directory fyi)
