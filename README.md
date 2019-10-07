# Neufeld lab 16S RNA analysis pipeline

## About
16S RNA analysis workflow based on qiime2 wrapped in luigi framework.

Currently, it uses conda 4.7.12 and qiime2 version 2019-07

**Note that previous versions of conda may cause problems**

## Required packages
**conda 4.7.12 or later** (No guarantee previous versions of conda will work!)  
**qiime2 (tested with 2019-04 and 2019-07)**

Refer to 16S-luigi.yml file for details.

## Setting up conda virtual environment (only has to be done once)

1. Clone this repository to your home directory.

```
cd ~
git clone https://github.com/danielm710/Neufeld-16S-Pipeline.git
```

2. Change to Neufeld-16S-Pipeline directory.

`cd Neufeld-16S-Pipeline`

### You don't have a qiime virtual environment yet OR You want to create a new conda environment for the pipeline

3.a. In this case, you can install conda environment directly from .yml file in this repository.

`conda env create --name <ENV_NAME> --file conda_env_file/16S-luigi.yml`

*Make sure to replace <ENV_NAME> with actual name*

e.g. `conda env create --name qiime_luigi --file conda_env_file/16S-luigi.yml`

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

5. Export `/Data/reference_databases/qiime2/qiime2-helpers/scripts` as a PATH variable (so that you can access Jackson's script on the server).

For people who are not familiar with commandline interface, you may follow the instruction below.

### Adding PATH variable Example

##### 1. Use your choice of text editor to open ~/.bashrc file.

For example, (I use "vim" text editor)

`vim ~/.bashrc`

##### 2. Go to the end of the file

For vim users, press G (uppercase G; it is case-sensitive!) 

##### 3. Add 'PATH=${PATH}:/Data/reference_databases/qiime2/qiime2-helpers/scripts' to the end of the file

For vim users, you may do the following...

&nbsp;&nbsp;&nbsp;a) Press Esc button however many times you want (just to make sure you are not in some weird mode). 2-3 times should suffice. 

&nbsp;&nbsp;&nbsp;b) Press o (lowercase alphabet 'o'). This should add a new line, and you will be able to type now.

&nbsp;&nbsp;&nbsp;c) Add the following lines

```
# Temporary PATH variable to access Jackson's script
PATH=${PATH}:/Data/reference_databases/qiime2/qiime2-helpers/scripts
```

&nbsp;&nbsp;&nbsp;d) Press Esc button once or twice

&nbsp;&nbsp;&nbsp;e) Press : (colon), and type wq to write and quit.

`:wq`

##### 4. In the terminal, run

`source ~/.bashrc`

If you don't run this command, any changes you made in .bashrc file will NOT take effects (until you close the terminal and restart it)

<br />

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

#### For people who are not comfortable with linux terminal

0. Activate conda environment and cd to Neufeld-16S-Pipeline (if you haven't already done so).

1. Generate configuration file by running luigi_config_generator.py.

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--sample-type <SAMPLE_TYPE [default = SampleData[PairedEndSequencesWithQuality]]> \
	--input-format <INPUT_FORMAT [default = PairedEndFastqManifestPhred33]> \
	--is-first <FIRST TIME RUNNING THIS SCRIPT?>
-----------------------------------------------------------------------------
- Actual Example -

python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--sample-type SampleData[PairedEndSequencesWithQuality] \
	--input-format PairedEndFastqManifestPhred33 \
	--is-first yes
```

Note that *you don't have to* specify `--sample-type` and `--input-format` if you're okay with the default values.  
If this is the case, simply run

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--is-first <FIRST TIME RUNNING THIS SCRIPT?>
-----------------------------------------------------------------------------
- Actual Example -

python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--is-first yes
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

You may examine "paired-end-demux.qzv" file in qiime2 View to determine trim and truncation cutoff.

3. Generate configuration file again (to specify other options).

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--trim-left-f <TRIM_LEFT_F_VALUE [default = 19]> \
	--trunc-len-f <TRUNC_LEN_F_VALUE [default = 250]> \
	--trim-left-r <TRIM_LEFT_R_VALUE [default = 20]> \
	--trunc-len-r <TRUNC_LEN_R_VALUE [default = 250]> \
	--classifier <PATH_TO_YOUR_CLASSIFIER_FILE [default = qiime2-2019-07 version]> \
	--is-first <FIRST TIME RUNNING THIS SCRIPT?>
-----------------------------------------------------------------------------
- Actual Example -
	
python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--trim-left-f 19 \
	--trunc-len-f 250 \
	--trim-left-r 20 \
	--trunc-len-r 250 \
	--classifier /Data/reference_databases/qiime2/training_classifier/silva132_V4V5_qiime2-2019.7/classifier_silva_132_V4V5.qza \
	--is-first no
```

_(Again) Note that if you are okay with default values, you can run the command below instead._

```
- General Format -

python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--is-first <FIRST TIME RUNNING THIS SCRIPT?>
-----------------------------------------------------------------------------
- Actual Example -

python luigi_config_generator.py \
	--manifest /Winnebago/danielm710/input/ManifestFile.txt \
	--is-first no
```

**_It is important that the classifier version MATCHES the qiime 2 version. It will throw an error otherwise_**

4. Run luigi pipeline to run the rest of the worflow.

```
python 16S_pipeline.py Run_All --local-scheduler
```

When it's done running, your screen should look something like this (takes some time to run)

```
===== Luigi Execution Summary =====

Scheduled 12 tasks of which:
* 2 complete ones were encountered:
    - 1 Import_Data(sample_type=SampleData[PairedEndSequencesWithQuality], input_format=PairedEndFastqManifestPhred33)
    - 1 Summarize()
* 10 ran successfully:
    - 1 Convert_Biom_to_TSV()
    - 1 Denoise(trim_left_f=19, trunc_len_f=250, trim_left_r=20, trunc_len_r=250, n_threads=10)
    - 1 Denoise_Tabulate()
    - 1 Export_Feature_Table()
    - 1 Export_Representative_Seqs()
    ...

This progress looks :) because there were no failed tasks or missing dependencies

===== Luigi Execution Summary =====
```

5. Your "output" directory (directory named "output") should look something like this

```
output/
├── dada2
│   ├── dada2_log.txt
│   ├── dada2-rep-seqs.qza
│   ├── dada2-table.qza
│   ├── stats-dada2.qza
│   └── stats-dada2.qzv
├── exported
│   ├── ASV_table_combined.log
│   ├── ASV_table_combined.tsv
│   ├── dna-sequences.fasta
│   ├── feature-table.biom
│   ├── feature-table.tsv
│   └── taxonomy.tsv
├── paired-end-demux.qza
├── paired-end-demux.qzv
└── taxonomy
    ├── taxonomy_log.txt
    ├── taxonomy.qza
    └── taxonomy.qzv
```

_if you don't see the above message (notice the smiley face, ":)"), or your output directory is missing some files, it means the pipeline is not successfully run. Check with the lab's bioinformatician if the error is not obvious_

6. Make sure to rename or move this directory to somewhere else when you are done running the pipeline.

**by default, luigi pipeline looks at "output" directory to check for successful tasks, so if all the files already exist in this directory (e.g. from analyzing your previous samples), it will think there aren't any jobs to be run for the new samples since all the files are there.**

##### Moving directory example
Let's say you want to move "output" directory to "Analysis" directory under the home directory, and rename it to "Illumina_Run3".

You may run the command below to do so.

`mv output ~/Analysis/Illumina_Run3` ("~" means home directory fyi)

#### For people who are fairly comfortable with linux terminal, AND know how to edit files from the terminal

1. Change directory to "configuration directory".

`cd configuration`

2. Copy template config file, and rename the copied config as luigi.cfg.

`cp template.cfg luigi.cfg`

3. Edit luigi.cfg to change qiime2 options.
4. cd to the previous dir and run pipeline to get the summary file.

```
cd ..
python 16S_pipeline.py Summarize --local-scheduler
```

5. Inspect the .qzv file, and edit `luigi.cfg` to modify parameters.

6. Run the pipeline again to finish the rest of the workflow.

`python 16S_pipeline.py Run_All --local-scheduler`
