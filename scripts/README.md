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
  --point-size <SCATTER PLOT DATA POINT SIZE. DEFAULT=6> \
  --alpha <TRANSPARENCY SCALE FROM 0 TO 1 (O = FULLY TRANSPARENT). DEFAULT=0.9> \
  --stroke <POINT BORDER THICKNESS (0 = NO BORDER). DEFAULT=0.6> \
  --pc-axis-one <FIRST PC AXIS TO PLOT. DEFAULT=PC1> \
  --pc-axis-two <SECOND PC AXIS TO PLOT. DEFAULT=PC2> \
  --output <PATH_TO_STORE_OUTPUT_AS. DEFAULT="./PCoA_plot.pdf"
 
---------------------------------------------------------------
-Actual Example-
python generate_pcoa.py \
  --pcoa-qza /Winnebago/danielm710/sample_data_AXIOME3/bray_curtis_pcoa.qza \
  --metadata /Winnebago/danielm710/sample_data_AXIOME3/metadata_MaCoTe.tsv \
  --target-primary Types \
  --target-secondary NTCGroup \
  --point-size 4 \
  --alpha 0.9 \
  --stroke 0.6 \
  --pc-axis-one PC1 \
  --pc-axis-two PC2 \
  --output myPlot
```

If run successfully, it should create a PDF file with a PCoA plot in it.

### Keep in mind...
1. `--target-primary` will be displayed in different **COLOURS** and  
`--target-secondary` will be displayed in different **SHAPES**
