# 2D PCoA Plot Generator Usage
0. Make sure QIIME2 conda environment is activated  
`conda activate <YOUR_ENVIRONMENT>`

**TIP!!!**  
You may list existing conda environments by running the command below in case you can't remember the name of the environnment.  
`conda env list`

1. Run the command below
```
-General Format-
python generate_pcoa.py \
  --pcoa-qza <PATH TO YOUR QIIME2 PCoA Artifact (.qza). REQUIRED> \
  --metadata <PATH TO YOUR METADATA. REQUIRED> \
  --target-primary <COLUMN IN METADATA YOU WANT TO VISUALIZE. REQUIRED> \
  --target-secondary <ADDITIONA COLUMN TO BE VISUALIZED. OPTINAL> \
  --point-size <SCATTER PLOT DATA POINT SIZE. DEFAULT=6>
  --output <PATH_TO_STORE_OUTPUT_AS. DEFAULT="./PCoA_plot.pdf"
 
---------------------------------------------------------------
-Actual Example-
python generate_pcoa.py \
  --input-qza /Winnebago/danielm710/katja_analysis/sample9/bray-curtis-pcoa_6000.qza \
  --metadata /Winnebago/danielm710/katja_analysis/sample9/MetadataHarwellPro.tsv \
  --target-primary SampleID2 \
  --target-secondary Cycle \
  --point-size 4
  --output myPlot.pdf
```

If run successfully, it should create a PDF file with a PCoA plot in it.

### Keep in mind...
1. `--target-primary` will be displayed in different **COLOURS** and  
`--target-secondary` will be displayed in different **SHAPES**