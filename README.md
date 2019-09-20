# Neufeld lab 16S RNA analysis pipeline

## About
16S RNA analysis workflow based on qiime2 wrapped in luigi framework.

Currently, it uses qiime2 version 2019-07

**Note that previous versions of qiim2 may cause problems**

## Required packages
Refer to 16S-luigi.yml file

You may run the following code to create conda virtual environment

`conda env create -f 16S-luigi.yml`

## Setting up conda virtual environment (only has to be done once)

1. Clone this repository to your home directory.

```
cd ~
git clone https://github.com/danielm710/Neufeld-16S-Pipeline.git
```

2. Change to Neufeld-16S-Pipeline directory.

`cd Neufeld-16S-Pipeline`

<br />

**_"Installation step diverges from here depending on your existing virtual environment."_**

<br />

### You don't have a qiime virtual environment yet

3.a. In this case, you can install conda environment directly from .yml file in this repository.

`conda env create --name <ENV_NAME> --file conda_env_file/16S-luigi.yml`

### You already have an existing conda environment for qiime2 version 2019-07
<br />
3.b. In this case, you should just do...

##### i) activate your qiime environment 

`conda activate <YOUR_QIIME_ENV>`

##### ii) Make sure pip and python are pointing to anaconda packages **not to /usr/bin**

`which pip` should display something like `/Winnebago/danielm710/anaconda3/envs/qiime2-2019.7/bin/pip`

`which python` should display something like `/Winnebago/danielm710/anaconda3/envs/qiime2-2019.7/bin/python`

##### iii) Install luigi by running the command...

`pip install luigi`

##### iv) Install BioPython and pandas (Jackson's script depends on these packages)

`conda install -c bioconda biopython pandas`

<br />

**_Installation step converges from here_**

<br />
	
4. Activate your qiime2 environment (if you already activated, ignore this step).

`conda activate <QIIME_ENV>`

5. Add PATH variable (so that you can access Jackson's script on the server).

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

<br />

## Usage

### For people who are not comfortable with linux terminal

0. Activate conda environment and cd to Neufeld-16S-Pipeline (if you haven't already done so).

1. Generate configuration file by running luigi_config_generator.py.

```
python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--sample-type <SAMPLE_TYPE [default = SampleData[PairedEndSequencesWithQuality]]> \
	--input-format <INPUT_FORMAT [default = PairedEndFastqManifestPhred33]>
```

Note that *you don't have to* specify `--sample-type` and `--input-format` if you're okay with the default settings.  
If this is the case, simply do

```
python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> 
```

2. Run luigi pipeline to generate summary file for you to examine it.

```
python 16S_pipeline.py Summarize --local-scheduler
```

When it's done running you should see something like this

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
python luigi_config_generator.py \
	--manifest <PATH_TO_YOUR_MANIFEST_FILE> \
	--trim-left-f <TRIM_LEFT_F_VALUE [default = 19]> \
	--trunc-len-f <TRUNC_LEN_F_VALUE [default = 250]> \
	--trim-left-r <TRIM_LEFT_R_VALUE [default = 20]> \
	--trunc-len-r <TRUNC_LEN_R_VALUE [default = 250]> \
	--classifier <PATH_TO_YOUR_CLASSIFIER_FILE [default = qiime2-2019-07 version]>
```

_Note that if you do NOT specify path to taxonomy classifier, it will use qiim2-2019-07 version by default._

**_It is important that the classifier version that MATCHES the qiime 2 version. It will throw an error otherwise_**

4. Run luigi pipeline to run the rest of the worflow.

```
python 16S_pipeline.py Production_Mode --local-scheduler
```

5. This will create the output directory that contains all your outputs. Make sure to move/clean up this directory after your done.

**luigi may not run if this directory is not properly cleaned up**

### For people who are fairly comfortable with linux terminal, AND know how to edit files from the terminal

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

`python 16S_pipeline.py Production_Mode --local-scheduler`
