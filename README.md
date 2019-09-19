# Neufeld lab 16S RNA analysis pipeline

## About
16S RNA analysis workflow based on qiime2 wrapped in luigi framework.

Currently, it uses qiime2 version 2019-07

## Required packages
Refer to 16S-luigi.yml file

You may run the following code to create conda virtual environment

`conda env create -f 16S-luigi.yml`

## Usage

### 1. Set up conda virtual environment

#### You already have a conda environment for qiime2

In this case, you do not necessarily need to install a new virtual environment from .yml file.

You should just do...



1. activate your qiime environment 

`conda activate <YOUR_QIIME_ENV>`

2. Make sure pip and python are pointing to anaconda packages *not to /usr/bin*

`which pip` should display something like `/Winnebago/danielm710/anaconda3/envs/qiime2-2019.7/bin/pip`

`which python` should display something like `/Winnebago/danielm710/anaconda3/envs/qiime2-2019.7/bin/python`

3. Install luigi by running the command...

`pip install luigi`

4. Install BioPython and pandas (Jackson's script depends on these packages)

`conda install -c bioconda biopython pandas`

5. Add PATH variable (so that you can access Jackson's script in the server)

For people who are not familiar with command line interface, you may follow the guideline below.

......1. Use your choice of text editor to open ~/.bashrc file.

.........For example, (I use "vim" text editor)

.........`vim ~/.bashrc`

......2. Go to the end of the file

.........For vim users, you can press G (uppercase G; it is case-sensitive!) 

......3. Add 'PATH=${PATH}:/Data/reference/databases/qiime2/qiime2-helpers/scripts' to the end of the file

.........For vim users, do the following steps...

............a) Press Esc button however many times you want (just to make sure you are not in some weird mode). 2-3 times should suffice. 

............b) Press o (lowercase alphabet 'o'). This should add a new line, and you will be able to type now.

............c) Add the following lines

		```
		# Temporary PATH variable to access Jackson's script
		PATH=${PATH}:/Data/reference_databases/qiime2/qiime2-helpers/scripts
		```

............d) Press Esc button once or twice

............e) Press : (colon), and type wq to save and exit

`:wq`


```
