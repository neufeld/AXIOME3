import luigi
import os
import sys
#from subprocess import check_output, CalledProcessError
import subprocess
import logging
import pandas as pd
from textwrap import dedent

# Import custom modules
from scripts.qiime2_helper.summarize_sample_counts import (
    load_qiime2_artifact,
    generate_sample_count,
    get_sample_count
)
from scripts.qiime2_helper.generate_combined_feature_table import combine_table
from scripts.qiime2_helper import artifact_helper
from scripts.qiime2_helper.generate_multiple_pcoa import (
        generate_pdf,
        generate_images,
        save_as_json
)
from scripts.qiime2_helper.split_manifest_file_by_run_ID import (
    split_manifest
)

# Define custom logger
logger = logging.getLogger("luigi logger")

## Path to configuration file to be used
#if("LUIGI_CONFIG_PATH" not in os.environ):
#    raise FileNotFoundError("Add LUIGI_CONFIG_PATH to environment variable!")
#
#config_path = os.environ["LUIGI_CONFIG_PATH"]
#luigi.configuration.add_config_path(config_path)

# Path to configuration file to be used
config_path = os.environ.get('LUIGI_CONFIG_PATH', "/pipeline/AXIOME3/configuration/luigi.cfg")
luigi.configuration.add_config_path(config_path)

# Script directory
script_dir = "scripts"

# QIIME2 helper directory
qiime2_helper_dir = os.path.join(script_dir, "qiime2_helper")

# FAPROTAX directory with database file and script
FAPROTAX = "FAPROTAX"

def auto_sampling_depth(feature_table_artifact):
    # Get the lowest sequence read in the samples
    feature_table_df = load_qiime2_artifact(feature_table_artifact)
    sample_count_df = generate_sample_count(feature_table_df)

    # convert to int
    sample_count_df['Count'] = sample_count_df['Count'].round(0).astype(int)

    min_count = sample_count_df['Count'].min() if (sample_count_df['Count'].min() > 0) else 1

    return str(min_count)

def run_cmd(cmd, step):
    #try:
    #    output = check_output(cmd)
    #except CalledProcessError as err:
    #    logger.error("In {step} following error occured\n{err}".format(
    #        step=step,
    #        err=err
    #        ))
    #    raise err
    #except Exception as err:
    #    logger.error("In {step} unknown error occured\n{err}".format(
    #        step=step,
    #        err=err
    #        ))
    #    raise err
    #finally:
    #    logger.error(output)

    proc = subprocess.Popen(cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()

    return_code = proc.returncode

    if not(return_code == 0):
        combined_msg = (stdout + stderr).decode('utf-8')
        err_msg = "In {step}, the following command, : ".format(step=step) + \
                "{cmd}\n\n".format(cmd=cmd) + \
                "resulted in an error:\n{combined_msg}"\
                        .format(combined_msg=combined_msg)

        web_err_msg = "<-->" + combined_msg + "<-->"

        logger.error(err_msg)
        raise ValueError(web_err_msg)
    else:
        return stdout

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    # Return false for all other strings
    else:
        return False

    #elif v.lower() in ('no', 'false', 'f', 'n', '0'):
    #    return False
    #else:
    #    raise argparse.ArgumentTypeError('Boolean value expected.')

class Out_Prefix(luigi.Config):
    prefix = luigi.Parameter()

class Output_Dirs(luigi.Config):
    # Define output paths
    out_dir = Out_Prefix().prefix
    input_upload_dir = os.path.join(out_dir, "input_upload")
    manifest_dir = os.path.join(out_dir, "manifest")
    denoise_dir = os.path.join(out_dir, "denoise")
    rarefy_dir = os.path.join(out_dir, "rarefy")
    taxonomy_dir = os.path.join(out_dir, "taxonomic_classification")
    analysis_dir = os.path.join(out_dir, "analysis")

    export_dir = os.path.join(out_dir, "exported")
    rarefy_export_dir = os.path.join(out_dir, "rarefy_exported")
    phylogeny_dir = os.path.join(analysis_dir, "phylogeny")
    collapse_dir = os.path.join(out_dir, "taxa_collapse")

    post_analysis_dir = os.path.join(out_dir, "post_analysis")
    filtered_dir = os.path.join(post_analysis_dir, "filtered")
    filtered_taxonomy_dir = os.path.join(filtered_dir, "taxonomy")
    core_metric_dir = os.path.join(analysis_dir, "metrics")
    alpha_sig_dir = os.path.join(post_analysis_dir, "alpha_group_significance")
    pcoa_dir = os.path.join(analysis_dir, "pcoa_plots")
    faprotax_dir = os.path.join(post_analysis_dir, "FAPROTAX")
    picrust_dir = os.path.join(post_analysis_dir, "PICRUST2")

    visualization_dir = os.path.join(out_dir, "visualization")

class Samples(luigi.Config):
    """
    Global variables that multiple steps may need access to.
    Includes...
        1. Manifest file (.txt) (maybe only accept .txt extension?)

    """
    manifest_file = luigi.Parameter()
    metadata_file = luigi.Parameter(default='')
    is_multiple = luigi.Parameter(default='n')
    sampling_depth = luigi.Parameter(default='10000')

    def get_samples(self):
        # If manifest file not specified by user, return
        if(self.manifest_file == "<MANIFEST_PATH>"):
            return

        manifest_df = pd.read_csv(self.manifest_file, index_col=0)

        # Return set of sample IDs if multiple IDs found
        if('run_ID' in manifest_df.columns):
            return set(manifest_df['run_ID'])
        # Return empty set if single run
        else:
            return set()

class Split_Samples(luigi.Task):
    """
    Split samples based on metadata
    """
    out_dir = Output_Dirs().manifest_dir

    def output(self):
        samples = Samples().get_samples()
        is_multiple = str2bool(Samples().is_multiple)

        # If multiple runs are specified in manifest file
        if(is_multiple):
            output = {}
            for sample in samples:
                manifest = "manifest_" + str(sample) + ".csv"
                out_path = os.path.join(self.out_dir, manifest)

                output[str(sample)] = luigi.LocalTarget(out_path)

            return output
        # Single run case
        else:
            output = os.path.join(self.out_dir, "manifest.csv")

            return luigi.LocalTarget(output)

    def run(self):
        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        # Split manifest if multiple runs in manifest file
        manifest_path = Samples().manifest_file
        is_multiple = str2bool(Samples().is_multiple)

        if(is_multiple):
            split_manifest(manifest_path, self.out_dir)
        else:
            cmd = ['cp',
                    manifest_path,
                    self.output().path]

            run_cmd(cmd, self)

class Import_Data(luigi.Task):
    # Options for qiime tools import
    sample_type = luigi.Parameter(
            default='SampleData[PairedEndSequencesWithQuality]')
    input_format = luigi.Parameter(default="PairedEndFastqManifestPhred33")

    out_dir = Output_Dirs().input_upload_dir
    samples = Samples().get_samples()
    is_multiple = str2bool(Samples().is_multiple)

    def requires(self):
        return Split_Samples()

    def output(self):
        # Multiple run specified in the manifest file
        if(self.is_multiple):
            output = {}
            for sample in self.samples:
                prefix = str(sample) + "_paired_end_demux.qza"
                paired_end_demux = os.path.join(self.out_dir, prefix)

                output[str(sample)] = luigi.LocalTarget(paired_end_demux)

            return output
        # Single  run case
        else:
            paired_end_demux = os.path.join(self.out_dir, "paired_end_demux.qza")

            return luigi.LocalTarget(paired_end_demux)

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                step)

        #inputPath = Samples().manifest_file
        #
        ## Make sure input file actually exists
        #try:
        #    with open(inputPath, 'r') as fh:
        #        fh.readlines()
        #except FileNotFoundError:
        #    logger.error("Input file for qiime tools import does not exist...")
        #    raise
        ## in case of unexpected errors
        #except Exception as err:
        #    logger.error(
        #    "In Import_Data() following error occured\n" + str(err))
        #    raise

        # Multiple run
        if(self.is_multiple):
            for sample in self.samples:
                cmd = ["qiime",
                        "tools",
                        "import",
                        "--type",
                        self.sample_type,
                        "--input-path",
                        self.input()[str(sample)].path,
                        "--output-path",
                        self.output()[str(sample)].path,
                        "--input-format",
                        self.input_format]
                run_cmd(cmd, self)
        # Single run
        else:
            inputPath = Samples().manifest_file
            cmd = ["qiime",
                    "tools",
                    "import",
                    "--type",
                    self.sample_type,
                    "--input-path",
                    inputPath,
                    "--output-path",
                    self.output().path,
                    "--input-format",
                    self.input_format]

            run_cmd(cmd, self)

class Summarize(luigi.Task):
    samples = Samples().get_samples()
    is_multiple = str2bool(Samples().is_multiple)
    out_dir = Output_Dirs().input_upload_dir

    def requires(self):
        return Import_Data()

    def output(self):
        # Multiple run
        if(self.is_multiple):
            output = {}
            for sample in self.samples:
                prefix = str(sample) + "_paired_end_demux.qzv"
                paired_end_demux = os.path.join(self.out_dir, prefix)

                output[str(sample)] = luigi.LocalTarget(paired_end_demux)

            return output
        # Single run
        else:
            summary_file = os.path.join(self.out_dir, "paired_end_demux.qzv")

            return luigi.LocalTarget(summary_file)

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().out_dir],
                step)

        # Multiple run
        if(self.is_multiple):
            for sample in self.samples:
            # Generate summary file
                cmd = ["qiime",
                        "demux",
                        "summarize",
                        "--i-data",
                        self.input()[str(sample)].path,
                        "--o-visualization",
                        self.output()[str(sample)].path]

                run_cmd(cmd, self)
        # Single run
        else:
            # Generate summary file
            cmd = ["qiime",
                    "demux",
                    "summarize",
                    "--i-data",
                    self.input().path,
                    "--o-visualization",
                    self.output().path]

            run_cmd(cmd, self)

class Denoise(luigi.Task):
    trim_left_f = luigi.Parameter(default="19")
    trunc_len_f = luigi.Parameter(default="250")
    trim_left_r = luigi.Parameter(default="20")
    trunc_len_r = luigi.Parameter(default="250")
    n_cores = luigi.Parameter(default="1")

    samples = Samples().get_samples()
    is_multiple = str2bool(Samples().is_multiple)
    denoise_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Import_Data()

    def output(self):
        # Multiple runs
        if(self.is_multiple):
            output = {}
            for sample in self.samples:
                table_prefix = str(sample) + "_dada2_table.qza"
                seq_prefix = str(sample) + "_dada2_rep_seqs.qza"
                stats_prefix = str(sample) + "_stats_dada2.qza"
                log_prefix = str(sample) + "_dada2_log.txt"

                denoise_table = os.path.join(self.denoise_dir,
                        str(sample), table_prefix)
                rep_seqs = os.path.join(self.denoise_dir,
                        str(sample), seq_prefix)
                denoise_stats = os.path.join(self.denoise_dir,
                        str(sample), stats_prefix)
                dada2_log = os.path.join(self.denoise_dir,
                        str(sample), log_prefix)

                denoise_out = {
                        "table": luigi.LocalTarget(denoise_table),
                        "rep_seqs": luigi.LocalTarget(rep_seqs),
                        "stats": luigi.LocalTarget(denoise_stats),
                        "log": luigi.LocalTarget(dada2_log, format=luigi.format.Nop)
                        }

                output[str(sample)] = denoise_out
            return output
        # Single run
        else:
            denoise_table = os.path.join(self.denoise_dir, "dada2_table.qza")
            rep_seqs = os.path.join(self.denoise_dir, "dada2_rep_seqs.qza")
            denoise_stats = os.path.join(self.denoise_dir, "stats_dada2.qza")
            dada2_log = os.path.join(self.denoise_dir, "dada2_log.txt")

            out = {
                    "table": luigi.LocalTarget(denoise_table),
                    "rep_seqs": luigi.LocalTarget(rep_seqs),
                    "stats": luigi.LocalTarget(denoise_stats),
                    "log": luigi.LocalTarget(dada2_log, format=luigi.format.Nop)
                    }

            return out

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.denoise_dir],
                self)

        if(self.is_multiple):
            # Get cutoff for each sample
            #trim_left_f_list = self.trim_left_f.split(',')
            #trunc_len_f_list = self.trunc_len_f.split(',')
            #trim_left_r_list = self.trim_left_r.split(',')
            #trunc_len_r_list = self.trunc_len_r.split(',')

            #trim_left_f_dict = {}
            #trunc_len_f_dict = {}
            #trim_left_r_dict = {}
            #trunc_len_r_dict = {}

            #for trim_f in trim_left_f_list:
            #    sample_id = trim_f.split(':')[0].strip()
            #    cutoff = trim_f.split(':')[1].strip()

            #    trim_left_f_dict[sample_id] = cutoff

            #for trunc_f in trunc_len_f_list:
            #    sample_id = trunc_f.split(':')[0].strip()
            #    cutoff = trunc_f.split(':')[1].strip()

            #    trunc_len_f_dict[sample_id] = cutoff

            #for trim_r in trim_left_r_list:
            #    sample_id = trim_r.split(':')[0].strip()
            #    cutoff = trim_r.split(':')[1].strip()

            #    trim_left_r_dict[sample_id] = cutoff

            #for trunc_r in trunc_len_r_list:
            #    sample_id = trunc_r.split(':')[0].strip()
            #    cutoff = trunc_r.split(':')[1].strip()

            #    trunc_len_r_dict[sample_id] = cutoff

            # Run dada2 for each sample
            for sample in self.samples:
                # Run dada2
                #cmd = ["qiime",
                #        "dada2",
                #        "denoise-paired",
                #        "--i-demultiplexed-seqs",
                #        self.input()[str(sample)].path,
                #        "--p-trim-left-f",
                #        trim_left_f_dict[str(sample)],
                #        "--p-trunc-len-f",
                #        trunc_len_f_dict[str(sample)],
                #        "--p-trim-left-r",
                #        trim_left_r_dict[str(sample)],
                #        "--p-trunc-len-r",
                #        trunc_len_r_dict[str(sample)],
                #        "--p-n-threads",
                #        self.n_threads,
                #        "--o-table",
                #        self.output()[str(sample)]["table"].path,
                #        "--o-representative-sequences",
                #        self.output()[str(sample)]["rep_seqs"].path,
                #        "--o-denoising-stats",
                #        self.output()[str(sample)]["stats"].path,
                #        "--verbose"]

                # Make output directory
                run_cmd(['mkdir',
                        '-p',
                        os.path.join(self.denoise_dir, str(sample))],
                        self)

                cmd = ["qiime",
                        "dada2",
                        "denoise-paired",
                        "--i-demultiplexed-seqs",
                        self.input()[str(sample)].path,
                        "--p-trim-left-f",
                        self.trim_left_f,
                        "--p-trunc-len-f",
                        self.trunc_len_f,
                        "--p-trim-left-r",
                        self.trim_left_r,
                        "--p-trunc-len-r",
                        self.trunc_len_r,
                        "--p-n-threads",
                        self.n_cores,
                        "--o-table",
                        self.output()[str(sample)]["table"].path,
                        "--o-representative-sequences",
                        self.output()[str(sample)]["rep_seqs"].path,
                        "--o-denoising-stats",
                        self.output()[str(sample)]["stats"].path,
                        "--verbose"]

                output = run_cmd(cmd, self)

                # Write a log file
                with self.output()[str(sample)]["log"].open('wb') as fh:
                    fh.write(output)
        else:
            # Run dada2
            cmd = ["qiime",
                    "dada2",
                    "denoise-paired",
                    "--i-demultiplexed-seqs",
                    self.input().path,
                    "--p-trim-left-f",
                    self.trim_left_f,
                    "--p-trunc-len-f",
                    self.trunc_len_f,
                    "--p-trim-left-r",
                    self.trim_left_r,
                    "--p-trunc-len-r",
                    self.trunc_len_r,
                    "--p-n-threads",
                    self.n_cores,
                    "--o-table",
                    self.output()["table"].path,
                    "--o-representative-sequences",
                    self.output()["rep_seqs"].path,
                    "--o-denoising-stats",
                    self.output()["stats"].path,
                    "--verbose"]

            output = run_cmd(cmd, self)

            # Write a log file
            with self.output()["log"].open('wb') as fh:
                fh.write(output)

class Merge_Denoise(luigi.Task):
    samples = Samples().get_samples()
    is_multiple = str2bool(Samples().is_multiple)
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Denoise()

    def output(self):
        merged_table = os.path.join(self.out_dir, "merged_table.qza")
        merged_seqs = os.path.join(self.out_dir, "merged_rep_seqs.qza")

        output = {
                'table': luigi.LocalTarget(merged_table),
                'rep_seqs': luigi.LocalTarget(merged_seqs)
                }

        return output

    def run(self):
        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        # Multiple runs
        if(self.is_multiple):
            table_cmd = ['qiime',
                        'feature-table',
                        'merge',
                        '--o-merged-table',
                        self.output()['table'].path]

            seqs_cmd = ['qiime',
                        'feature-table',
                        'merge-seqs',
                        '--o-merged-data',
                        self.output()['rep_seqs'].path]

            for sample in self.samples:
                table_cmd.append('--i-tables')
                table_cmd.append(self.input()[str(sample)]['table'].path)

                seqs_cmd.append('--i-data')
                seqs_cmd.append(self.input()[str(sample)]['rep_seqs'].path)

            run_cmd(table_cmd, self)
            run_cmd(seqs_cmd, self)
        # Single run
        else:
            run_cmd(['cp',
                    self.input()['table'].path,
                    self.output()['table'].path],
                    self)

            run_cmd(['cp',
                    self.input()['rep_seqs'].path,
                    self.output()['rep_seqs'].path],
                    self)

class Merge_Denoise_Stats(luigi.Task):
    dada2_dir = Output_Dirs().denoise_dir
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Denoise()

    def output(self):
        merged_denoise_stats = os.path.join(self.out_dir, "merged_stats_dada2.qza")
        merged_denoise_json = os.path.join(self.out_dir, "merged_stats_dada2.json")

        output = {
            "qza": luigi.LocalTarget(merged_denoise_stats),
            "json": luigi.LocalTarget(merged_denoise_json)
        }
        return output

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        stats_df = artifact_helper.combine_dada2_stats_as_df(self.dada2_dir)
        stats_artifact = artifact_helper.import_dada2_stats_df_to_q2(stats_df)

        stats_df.to_json(self.output()["json"].path, orient='index')
        stats_artifact.save(self.output()["qza"].path)

class Sample_Count_Summary(luigi.Task):
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Merge_Denoise()

    def output(self):
        summary_file_tsv = os.path.join(self.out_dir, "sample_counts.tsv")
        summary_file_json = os.path.join(self.out_dir, "sample_counts.json")
        log_file = os.path.join(self.out_dir, "log.txt")

        output = {
            "tsv": luigi.LocalTarget(summary_file_tsv),
            "json": luigi.LocalTarget(summary_file_json)
        }

        return output

    def run(self):
        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        get_sample_count(
                self.input()['table'].path,
                self.output()["tsv"].path,
                self.output()["json"].path)

class Taxonomic_Classification(luigi.Task):
    classifier = luigi.Parameter()
    n_cores = luigi.Parameter(default="1")

    out_dir = Output_Dirs().taxonomy_dir

    def requires(self):
        return Merge_Denoise()

    def output(self):
        classified_taxonomy = os.path.join(self.out_dir, "taxonomy.qza")

        output = {
                "taxonomy": luigi.LocalTarget(classified_taxonomy),
                }

        return output

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        # Run qiime classifier
        cmd = ["qiime",
                "feature-classifier",
                "classify-sklearn",
                "--i-classifier",
                self.classifier,
                "--i-reads",
                self.input()["rep_seqs"].path,
                "--o-classification",
                self.output()["taxonomy"].path,
                "--p-n-jobs",
                self.n_cores,
                "--verbose"]

        output = run_cmd(cmd, self)

class Export_Feature_Table(luigi.Task):
    export_dir = Output_Dirs().export_dir

    def requires(self):
        return Merge_Denoise()

    def output(self):
        biom = os.path.join(self.export_dir, "feature-table.biom")

        return luigi.LocalTarget(biom)

    def run(self):
        # Make directory
        run_cmd(["mkdir",
                "-p",
                self.export_dir],
                self)

        # Export file
        cmd = ["qiime",
                "tools",
                "export",
                "--input-path",
                self.input()["table"].path,
                "--output-path",
                os.path.dirname(self.output().path)]

        run_cmd(cmd, self)

class Export_Taxonomy(luigi.Task):
    out_dir = Output_Dirs().taxonomy_dir

    def requires(self):
        return Taxonomic_Classification()

    def output(self):
        tsv = os.path.join(self.out_dir, "taxonomy.tsv")

        return luigi.LocalTarget(tsv)

    def run(self):
        step = str(self)
        # Make directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                step)

        # Export file
        cmd = ["qiime",
                "tools",
                "export",
                "--input-path",
                self.input()["taxonomy"].path,
                "--output-path",
                os.path.dirname(self.output().path)]

        run_cmd(cmd, step)

class Export_Representative_Seqs(luigi.Task):
    out_dir = Output_Dirs().analysis_dir

    def requires(self):
        return Merge_Denoise()

    def output(self):
        fasta = os.path.join(self.out_dir, "dna-sequences.fasta")

        return luigi.LocalTarget(fasta)

    def run(self):
        # Make directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        # Export file
        cmd = ["qiime",
                "tools",
                "export",
                "--input-path",
                self.input()["rep_seqs"].path,
                "--output-path",
                os.path.dirname(self.output().path)]

        run_cmd(cmd, self)

class Convert_Feature_Table_to_TSV(luigi.Task):
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Merge_Denoise()

    def output(self):
        tsv = os.path.join(self.out_dir, "feature-table.tsv")

        return luigi.LocalTarget(tsv)

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                step)

        # Convert to TSV
        output = artifact_helper.convert(self.input()["table"].path)
        collapsed_df = output["feature_table"]

        collapsed_df.T.to_csv(
            self.output().path,
            sep="\t",
            index_label="SampleID"
        ) 

class Generate_Combined_Feature_Table(luigi.Task):
    out_dir = Output_Dirs().analysis_dir

    def requires(self):
        return {
                "Taxonomic_Classification": Taxonomic_Classification(),
                "Export_Representative_Seqs": Export_Representative_Seqs(),
                "Merge_Denoise": Merge_Denoise(),
                }

    def output(self):
        combined_table = os.path.join(self.out_dir, "ASV_table_combined.tsv")
        log = os.path.join(self.out_dir, "ASV_table_combined.log")


        output = {
                "table": luigi.LocalTarget(combined_table),
                #"log": luigi.LocalTarget(log, format=luigi.format.Nop),
                }

        return output

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        combine_table(self.input()["Merge_Denoise"]["table"].path,
                    self.input()["Export_Representative_Seqs"].path,
                    self.input()["Taxonomic_Classification"]["taxonomy"].path,
                    self.output()["table"].path)

        # Write log files
        #with self.output()["log"].open('w') as fh:
        #    fh.write(logged_pre_rarefied)

class Phylogeny_Tree(luigi.Task):
    out_dir = Output_Dirs().phylogeny_dir
    n_cores = luigi.Parameter(default="1")

    def requires(self):
        return Merge_Denoise()

    def output(self):
        alignment = os.path.join(self.out_dir,
                "aligned_rep_seqs.qza")
        masked_alignment = os.path.join(self.out_dir,
                "masked_aligned_rep_seqs.qza")
        tree = os.path.join(self.out_dir,
                "unrooted_tree.qza")
        rooted_tree = os.path.join(self.out_dir,
                "rooted_tree.qza")

        out = {
            'alignment': luigi.LocalTarget(alignment),
            'masked_alignment': luigi.LocalTarget(masked_alignment),
            'tree': luigi.LocalTarget(tree),
            'rooted_tree': luigi.LocalTarget(rooted_tree),
        }

        return out

    def run(self):
        # Create output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir], self)

        # Make phylogeny tree
        cmd = ['qiime',
                'phylogeny',
                'align-to-tree-mafft-fasttree',
                '--i-sequences',
                self.input()['rep_seqs'].path,
                '--p-n-threads',
                self.n_cores,
                '--o-alignment',
                self.output()['alignment'].path,
                '--o-masked-alignment',
                self.output()['masked_alignment'].path,
                '--o-tree',
                self.output()['tree'].path,
                '--o-rooted-tree',
                self.output()['rooted_tree'].path
        ]

        run_cmd(cmd, self)

class Taxa_Collapse(luigi.Task):
    out_dir = Output_Dirs().taxonomy_dir

    def requires(self):
        return {"Merge_Denoise": Merge_Denoise(),
                "Taxonomic_Classification": Taxonomic_Classification()
                }

    def output(self):
        domain_collapsed_table = os.path.join(self.out_dir,
                "domain_collapsed_table.qza")
        phylum_collapsed_table = os.path.join(self.out_dir,
                "phylum_collapsed_table.qza")
        class_collapsed_table = os.path.join(self.out_dir,
                "class_collapsed_table.qza")
        order_collapsed_table = os.path.join(self.out_dir,
                "order_collapsed_table.qza")
        family_collapsed_table = os.path.join(self.out_dir,
                "family_collapsed_table.qza")
        genus_collapsed_table = os.path.join(self.out_dir,
                "genus_collapsed_table.qza")
        species_collapsed_table = os.path.join(self.out_dir,
                "species_collapsed_table.qza")

        output = {
            "domain": luigi.LocalTarget(domain_collapsed_table),
            "phylum": luigi.LocalTarget(phylum_collapsed_table),
            "class": luigi.LocalTarget(class_collapsed_table),
            "order": luigi.LocalTarget(order_collapsed_table),
            "family": luigi.LocalTarget(family_collapsed_table),
            "genus": luigi.LocalTarget(genus_collapsed_table),
            "species": luigi.LocalTarget(species_collapsed_table)
        }

        return output

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        # Taxa collapse
        taxa_keys = ["domain", "phylum", "class", "order", "family", "genus",
                "species"]

        # Taxa level; 1=domain, 7=species
        level = 1
        for taxa in taxa_keys:
            cmd = ["qiime",
                    "taxa",
                    "collapse",
                    "--i-table",
                    self.input()["Merge_Denoise"]["table"].path,
                    "--i-taxonomy",
                    self.input()["Taxonomic_Classification"]["taxonomy"].path,
                    "--p-level",
                    str(level),
                    "--o-collapsed-table",
                    self.output()[taxa].path]

            level = level + 1

            run_cmd(cmd, self)

class Export_Taxa_Collapse(luigi.Task):
    out_dir = Output_Dirs().taxonomy_dir

    def requires(self):
        return Taxa_Collapse()

    def output(self):
        exported_domain_collapsed_table = os.path.join(self.out_dir,
                "domain_collapsed_table.tsv")
        exported_phylum_collapsed_table = os.path.join(self.out_dir,
                "phylum_collapsed_table.tsv")
        exported_class_collapsed_table = os.path.join(self.out_dir,
                "class_collapsed_table.tsv")
        exported_order_collapsed_table = os.path.join(self.out_dir,
                "order_collapsed_table.tsv")
        exported_family_collapsed_table = os.path.join(self.out_dir,
                "family_collapsed_table.tsv")
        exported_genus_collapsed_table = os.path.join(self.out_dir,
                "genus_collapsed_table.tsv")
        exported_species_collapsed_table = os.path.join(self.out_dir,
                "species_collapsed_table.tsv")

        output = {
            "domain": luigi.LocalTarget(exported_domain_collapsed_table),
            "phylum": luigi.LocalTarget(exported_phylum_collapsed_table),
            "class": luigi.LocalTarget(exported_class_collapsed_table),
            "order": luigi.LocalTarget(exported_order_collapsed_table),
            "family": luigi.LocalTarget(exported_family_collapsed_table),
            "genus": luigi.LocalTarget(exported_genus_collapsed_table),
            "species": luigi.LocalTarget(exported_species_collapsed_table)
        }

        return output

    def run(self):
        # Make output dir
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        # Taxa collapse
        taxa_keys = ["domain", "phylum", "class", "order", "family", "genus",
                "species"]

        for taxa in taxa_keys:
            output = artifact_helper.convert(self.input()[taxa].path)
            collapsed_df = output["feature_table"]

            collapsed_df.to_csv(self.output()[taxa].path, sep="\t",
                    index_label="SampleID")

class Filtered_Taxa_Collapse(luigi.Task):
    filtered_taxonomy_dir = Output_Dirs().filtered_taxonomy_dir

    def requires(self):
        return {"Filter_Feature_Table": Filter_Feature_Table(),
                "Taxonomic_Classification": Taxonomic_Classification()
                }

    def output(self):
        domain_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "domain_collapsed_table.qza")
        phylum_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "phylum_collapsed_table.qza")
        class_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "class_collapsed_table.qza")
        order_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "order_collapsed_table.qza")
        family_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "family_collapsed_table.qza")
        genus_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "genus_collapsed_table.qza")
        species_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "species_collapsed_table.qza")

        output = {
            "domain": luigi.LocalTarget(domain_collapsed_table),
            "phylum": luigi.LocalTarget(phylum_collapsed_table),
            "class": luigi.LocalTarget(class_collapsed_table),
            "order": luigi.LocalTarget(order_collapsed_table),
            "family": luigi.LocalTarget(family_collapsed_table),
            "genus": luigi.LocalTarget(genus_collapsed_table),
            "species": luigi.LocalTarget(species_collapsed_table)
        }

        return output

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.filtered_taxonomy_dir],
                self)

        # Taxa collapse
        taxa_keys = ["domain", "phylum", "class", "order", "family", "genus",
                "species"]

        # Taxa level; 1=domain, 7=species
        level = 1
        for taxa in taxa_keys:
            cmd = ["qiime",
                    "taxa",
                    "collapse",
                    "--i-table",
                    self.input()["Filter_Feature_Table"].path,
                    "--i-taxonomy",
                    self.input()["Taxonomic_Classification"]["taxonomy"].path,
                    "--p-level",
                    str(level),
                    "--o-collapsed-table",
                    self.output()[taxa].path]

            level = level + 1

            run_cmd(cmd, self)

class Export_Filtered_Taxa_Collapse(luigi.Task):
    filtered_taxonomy_dir = Output_Dirs().filtered_taxonomy_dir

    def requires(self):
        return Filtered_Taxa_Collapse()

    def output(self):
        exported_domain_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "domain_collapsed_table.tsv")
        exported_phylum_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "phylum_collapsed_table.tsv")
        exported_class_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "class_collapsed_table.tsv")
        exported_order_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "order_collapsed_table.tsv")
        exported_family_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "family_collapsed_table.tsv")
        exported_genus_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "genus_collapsed_table.tsv")
        exported_species_collapsed_table = os.path.join(self.filtered_taxonomy_dir,
                "species_collapsed_table.tsv")

        output = {
            "domain": luigi.LocalTarget(exported_domain_collapsed_table),
            "phylum": luigi.LocalTarget(exported_phylum_collapsed_table),
            "class": luigi.LocalTarget(exported_class_collapsed_table),
            "order": luigi.LocalTarget(exported_order_collapsed_table),
            "family": luigi.LocalTarget(exported_family_collapsed_table),
            "genus": luigi.LocalTarget(exported_genus_collapsed_table),
            "species": luigi.LocalTarget(exported_species_collapsed_table)
        }

        return output

    def run(self):
        # Make output dir
        run_cmd(["mkdir",
                "-p",
                self.collapse_dir],
                self)

        # Taxa collapse
        taxa_keys = ["domain", "phylum", "class", "order", "family", "genus",
                "species"]

        for taxa in taxa_keys:
            output = artifact_helper.convert(self.input()[taxa].path)
            collapsed_df = output["feature_table"]

            collapsed_df.to_csv(self.output()[taxa].path, sep="\t",
                    index_label="SampleID")

# Post Analysis
# Filter sample by metadata
class Filter_Feature_Table(luigi.Task):
    metadata_file = Samples().metadata_file
    out_dir = Output_Dirs().analysis_dir

    def requires(self):
        return Merge_Denoise()

    def output(self):
        filtered_table = os.path.join(self.out_dir, "filtered_table.qza")

        return luigi.LocalTarget(filtered_table)

    def run(self):
        # Make output direcotry
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        # filter-sample command
        cmd = ["qiime",
                "feature-table",
                "filter-samples",
                "--i-table",
                self.input()["table"].path,
                "--m-metadata-file",
                self.metadata_file,
                "--o-filtered-table",
                self.output().path]

        run_cmd(cmd, self)

class Summarize_Filtered_Table(luigi.Task):
    filtered_dir = Output_Dirs().filtered_dir

    def requires(self):
        return Filter_Feature_Table()

    def output(self):
        summary_file_tsv = os.path.join(self.filtered_dir,
                "filtered_table_summary.tsv")
        summary_file_json = os.path.join(self.filtered_dir, "filtered_table_summary.json")

        output = {
            "tsv": luigi.LocalTarget(summary_file_tsv),
            "json": luigi.LocalTarget(summary_file_json)
        }

        return output

    def run(self):
        # Make output direcotry
        run_cmd(["mkdir",
                "-p",
                self.filtered_dir],
                self)

        get_sample_count(
                self.input().path,
                self.output()["tsv"].path,
                self.output()["json"].path)

class Export_Filtered_Table(luigi.Task):
    filtered_dir = Output_Dirs().filtered_dir

    def requires(self):
        return Filter_Feature_Table()

    def output(self):
        biom = os.path.join(self.filtered_dir, "filtered_feature-table.tsv")

        return luigi.LocalTarget(biom)

    def run(self):
        # Make output dir
        run_cmd(["mkdir",
                "-p",
                self.filtered_dir],
                self)

        output = artifact_helper.convert(self.input().path)
        collapsed_df = output["feature_table"]

        collapsed_df.T.to_csv(self.output().path, sep="\t",
                index_label="SampleID")

class Generate_Combined_Filtered_Feature_Table(luigi.Task):
    filtered_dir = Output_Dirs().filtered_dir

    def requires(self):
        return {
                "Export_Taxonomy": Export_Taxonomy(),
                "Export_Representative_Seqs": Export_Representative_Seqs(),
                "Export_Filtered_Table": Export_Filtered_Table(),
                }

    def output(self):
        combined_table = os.path.join(self.filtered_dir, "filtered_ASV_table_combined.tsv")
        log = os.path.join(self.filtered_dir, "ASV_table_combined.log")


        output = {
                "table": luigi.LocalTarget(combined_table),
                "log": luigi.LocalTarget(log, format=luigi.format.Nop),
                }

        return output

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.filtered_dir],
                self)

        combine_table(self.input()["Export_Filtered_Table"].path,
                    self.input()["Export_Representative_Seqs"].path,
                    self.input()["Export_Taxonomy"].path,
                    self.output()["table"].path)

# Most of these require rarefaction depth as a user parameter
class Core_Metrics_Phylogeny(luigi.Task):
    sampling_depth = Samples().sampling_depth
    metadata_file = Samples().metadata_file
    out_dir = Output_Dirs().core_metric_dir

    def requires(self):
        return {
                'Filter_Feature_Table': Filter_Feature_Table(),
                'Phylogeny_Tree': Phylogeny_Tree()
                }

    def output(self):
        rarefied_table = os.path.join(self.out_dir, "rarefied_table.qza")
        faith_pd_vector = os.path.join(self.out_dir, "alpha_faith_pd.qza")
        obs_otu_vector = os.path.join(self.out_dir, "alpha_observed_otus.qza")
        shannon_vector = os.path.join(self.out_dir, "alpha_shannon.qza")
        evenness_vector = os.path.join(self.out_dir, "alpha_evenness.qza")
        unweighted_unifrac_dist_matrix = os.path.join(self.out_dir,
                "unweighted_unifrac_distance.qza")
        weighted_unifrac_dist_matrix = os.path.join(self.out_dir,
                "weighted_unifrac_distance.qza")
        jaccard_dist_matrix = os.path.join(self.out_dir, "jaccard_distance.qza")
        bray_curtis_dist_matrix = os.path.join(self.out_dir,
                "bray_curtis_distance.qza")
        unweighted_unifrac_pcoa = os.path.join(self.out_dir,
                "unweighted_unifrac_pcoa.qza")
        weighted_unifrac_pcoa = os.path.join(self.out_dir,
                "weighted_unifrac_pcoa.qza")
        jaccard_pcoa = os.path.join(self.out_dir, "jaccard_pcoa.qza")
        bray_curtis_pcoa = os.path.join(self.out_dir, "bray_curtis_pcoa.qza")
        unweighted_unifrac_emperor = os.path.join(self.out_dir,
                "unweighted_unifrac_emperor.qzv")
        weighted_unifrac_emperor = os.path.join(self.out_dir,
                "weighted_unifrac_emperor.qzv")
        jaccard_emperor = os.path.join(self.out_dir, "jaccard_emperor.qzv")
        bray_curtis_emperor = os.path.join(self.out_dir, "bray_curtis_emperor.qzv")

        out = {
            'rarefied_table': luigi.LocalTarget(rarefied_table),
            'faith_pd_vector': luigi.LocalTarget(faith_pd_vector),
            'obs_otu_vector': luigi.LocalTarget(obs_otu_vector),
            'shannon_vector': luigi.LocalTarget(shannon_vector),
            'evenness_vector': luigi.LocalTarget(evenness_vector),
            'unweighted_unifrac_dist_matrix':
                luigi.LocalTarget(unweighted_unifrac_dist_matrix),
            'weighted_unifrac_dist_matrix':
                luigi.LocalTarget(weighted_unifrac_dist_matrix),
            'jaccard_dist_matrix': luigi.LocalTarget(jaccard_dist_matrix),
            'bray_curtis_dist_matrix':
                luigi.LocalTarget(bray_curtis_dist_matrix),
            'unweighted_unifrac_pcoa':
                luigi.LocalTarget(unweighted_unifrac_pcoa),
            'weighted_unifrac_pcoa': luigi.LocalTarget(weighted_unifrac_pcoa),
            'jaccard_pcoa': luigi.LocalTarget(jaccard_pcoa),
            'bray_curtis_pcoa': luigi.LocalTarget(bray_curtis_pcoa),
            'unweighted_unifrac_emperor':
                luigi.LocalTarget(unweighted_unifrac_emperor),
            'weighted_unifrac_emperor':
                luigi.LocalTarget(weighted_unifrac_emperor),
            'jaccard_emperor': luigi.LocalTarget(jaccard_emperor),
            'bray_curtis_emperor': luigi.LocalTarget(bray_curtis_emperor)
        }

        return out

    def run(self):
        # Make sure Metadata file is provided and exists
        if not(os.path.isfile(self.metadata_file)):
            msg = dedent("""
                    Metadata file is not provided or the provided Metadata file
                    does not exist!
                    """)

            raise FileNotFoundError(msg)

        # Create output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        # If sampling depth is 0, automatically determine sampling depth
        if(self.sampling_depth == '0'):
            sampling_depth = auto_sampling_depth(self.input()['Filter_Feature_Table'].path)
        else:
            sampling_depth = self.sampling_depth

        # Run core-metric-phylogenetic
        cmd = [
                'qiime',
                'diversity',
                'core-metrics-phylogenetic',
                '--i-table',
                self.input()['Filter_Feature_Table'].path,
                '--i-phylogeny',
                self.input()['Phylogeny_Tree']['rooted_tree'].path,
                '--p-sampling-depth',
                sampling_depth,
                '--o-rarefied-table',
                self.output()['rarefied_table'].path,
                '--o-faith-pd-vector',
                self.output()['faith_pd_vector'].path,
                '--o-observed-features-vector',
                self.output()['obs_otu_vector'].path,
                '--o-shannon-vector',
                self.output()['shannon_vector'].path,
                '--o-evenness-vector',
                self.output()['evenness_vector'].path,
                '--o-unweighted-unifrac-distance-matrix',
                self.output()['unweighted_unifrac_dist_matrix'].path,
                '--o-weighted-unifrac-distance-matrix',
                self.output()['weighted_unifrac_dist_matrix'].path,
                '--o-jaccard-distance-matrix',
                self.output()['jaccard_dist_matrix'].path,
                '--o-bray-curtis-distance-matrix',
                self.output()['bray_curtis_dist_matrix'].path,
                '--o-unweighted-unifrac-pcoa-results',
                self.output()['unweighted_unifrac_pcoa'].path,
                '--o-weighted-unifrac-pcoa-results',
                self.output()['weighted_unifrac_pcoa'].path,
                '--o-jaccard-pcoa-results',
                self.output()['jaccard_pcoa'].path,
                '--o-bray-curtis-pcoa-results',
                self.output()['bray_curtis_pcoa'].path,
                '--o-unweighted-unifrac-emperor',
                self.output()['unweighted_unifrac_emperor'].path,
                '--o-weighted-unifrac-emperor',
                self.output()['weighted_unifrac_emperor'].path,
                '--o-jaccard-emperor',
                self.output()['jaccard_emperor'].path,
                '--o-bray-curtis-emperor',
                self.output()['bray_curtis_emperor'].path
        ]

        # Add metadata information if present
        metadata = Samples().metadata_file
        if not(metadata == "<METADATA_PATH>" or
                metadata == ""):
            cmd.append('--m-metadata-file')
            cmd.append(metadata)

        run_cmd(cmd, self)

class Rarefy(luigi.Task):
    sampling_depth = luigi.Parameter(default="10000")

    rarefy_dir = Output_Dirs().rarefy_dir

    def requires(self):
        return Merge_Denoise()

    def output(self):
        rarefied_table = os.path.join(Output_Dirs().rarefy_dir,
                "rarefied_table.qza")

        return luigi.LocalTarget(rarefied_table)

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.rarefy_dir],
                self)

        # If sampling depth is 0, automatically determine sampling depth
        if(self.sampling_depth == '0'):
            sampling_depth = auto_sampling_depth(self.input()['Merge_Denoise'].path)
        else:
            sampling_depth = self.sampling_depth

        # Rarefy
        cmd = ["qiime",
                "feature-table",
                "rarefy",
                "--i-table",
                self.input()['table'].path,
                "--p-sampling-depth",
                sampling_depth,
                "--o-rarefied-table",
                self.output().path
                ]
        run_cmd(cmd, self)

class Export_Rarefy_Feature_Table(luigi.Task):

    def requires(self):
        return Rarefy()

    def output(self):
        rarefied_biom = os.path.join(Output_Dirs().rarefy_export_dir, "feature-table.biom")

        return luigi.LocalTarget(rarefied_biom)

    def run(self):
        step = str(self)
        # Make directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().rarefy_export_dir],
                step)

        # Export file
        cmd = ["qiime",
                "tools",
                "export",
                "--input-path",
                self.input().path,
                "--output-path",
                os.path.dirname(self.output().path)]

        run_cmd(cmd, step)

class Convert_Rarefy_Table_to_TSV(luigi.Task):

    def requires(self):
        return Rarefy()

    def output(self):
        tsv = os.path.join(Output_Dirs().rarefy_export_dir, "rarefied_feature_table.tsv")

        return luigi.LocalTarget(tsv)

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().rarefy_export_dir],
                step)

        # Convert to TSV
        output = artifact_helper.convert(self.input().path)
        collapsed_df = output["feature_table"]

        collapsed_df.T.to_csv(
            self.output().path,
            sep="\t",
            index_label="SampleID"
        )

        run_cmd(cmd, step)

class Generate_Combined_Rarefied_Feature_Table(luigi.Task):
    rarefy_export_dir = Output_Dirs().rarefy_export_dir

    def requires(self):
        return {
                "Export_Taxonomy": Export_Taxonomy(),
                "Export_Representative_Seqs": Export_Representative_Seqs(),
                "Convert_Rarefy_Table_to_TSV": Convert_Rarefy_Table_to_TSV()
                }

    def output(self):
        combined_rarefied_table = os.path.join(self.rarefy_export_dir,
                "ASV_rarefied_table_combined.tsv")
        rarefied_log = os.path.join(self.rarefy_export_dir,
                "ASV_rarefied_table_combined.log")

        output = {
                "rarefied_table": luigi.LocalTarget(combined_rarefied_table),
                #"rarefied_log": luigi.LocalTarget(rarefied_log,
                #    format=luigi.format.Nop)
                }

        return output

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.rarefy_export_dir],
                self)

        combine_table(self.input()["Convert_Rarefy_Table_to_TSV"].path,
                    self.input()["Export_Representative_Seqs"].path,
                    self.input()["Export_Taxonomy"].path,
                    self.output()["rarefied_table"].path)

class Subset_ASV_By_Abundance(luigi.Task):
    """
    Subsets ASV table by % abundance
    """
    export_dir = Output_Dirs().export_dir
    # Abundance threshold. Default is 1%
    threshold = luigi.Parameter(default="0.01")

    def requires(self):
        return Generate_Combined_Feature_Table()

    def output(self):
        abundance_subset = os.path.join(self.export_dir, "ASV_abundance_filtered.tsv")

        return luigi.LocalTarget(abundance_subset)

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.export_dir],
                self)

        # Run abundance subset script
        abundance_subset_script = os.path.join(qiime2_helper_dir,
                "filter_by_abundance.py")

        abundance_subset_cmd = ["python",
                                abundance_subset_script,
                                "--asv",
                                self.input()["table"].path,
                                "--threshold",
                                self.threshold,
                                "--output",
                                self.output().path]

        run_cmd(abundance_subset_cmd, self)

class Faprotax(luigi.Task):
    """
    Runs FAPROTAX (current version 1.2.1)
    """
    faprotax_dir = Output_Dirs().faprotax_dir

    def requires(self):
        return Subset_ASV_By_Abundance()

    def output(self):
        table = os.path.join(self.faprotax_dir, "functional_table.tsv")
        report = os.path.join(self.faprotax_dir, "report.txt")
        log = os.path.join(self.faprotax_dir, "log.txt")

        output = {
                "table": luigi.LocalTarget(table),
                "report": luigi.LocalTarget(report),
                "log": luigi.LocalTarget(log, format=luigi.format.Nop)
        }

        return output

    def run(self):
        # Make output dir
        run_cmd(['mkdir',
                '-p',
                self.faprotax_dir],
                self)

        # Path to faprotax script
        faprotax_script = os.path.join(FAPROTAX, "collapse_table.py")
        # Path to faprotax database
        faprotax_db = os.path.join(FAPROTAX, "FAPROTAX.txt")

        faprotax_cmd = ["python2",
                        faprotax_script,
                        '-i',
                        self.input().path,
                        '-o',
                        self.output()['table'].path,
                        '-g',
                        faprotax_db,
                        '-c',
                        "#",
                        '-d',
                        "Consensus.Lineage",
                        '--omit_columns',
                        "0,1",
                        '-r',
                        self.output()["report"].path,
                        '-n',
                        "columns_after_collapsing",
                        '--omit_samples',
                        "ReprSequence",
                        '--force',
                        '-v']

        faprotax_log = run_cmd(faprotax_cmd, self)

        with self.output()["log"].open('w') as fh:
            fh.write(faprotax_log)

class Picrust(luigi.Task):
    """
    Run PICRUST2 (installed as QIIME2 plugin)
    """
    picrust_dir = Output_Dirs().picrust_dir

    # PICRUST2 options
    threads = luigi.Parameter(default='6')
    p_hsp_method = luigi.Parameter(default='mp')
    max_nsti = luigi.Parameter(default='2')

    def requires(self):
        return Merge_Denoise()

    def output(self):
        pathway = os.path.join(self.picrust_dir, "pathway_abundance.qza")
        ec_metagenome = os.path.join(self.picrust_dir, "ec_metagenome.qza")
        ko_metagenome = os.path.join(self.picrust_dir, "ko_metagenome.qza")
        #log = os.path.join(self.picrust_dir, "log.txt")

        out = {
            "pathway": luigi.LocalTarget(pathway),
            "ec_metagenome": luigi.LocalTarget(ec_metagenome),
            "ko_metagenome": luigi.LocalTarget(ko_metagenome)
        #    "log": luigi.LocalTarget(log, format=luigi.format.Nop)
        }

        return out

    def run(self):
        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.picrust_dir]
                , self)

        # Run PICRUST2
        picrust_cmd = ['qiime',
                        'picrust2',
                        'full-pipeline',
                        '--i-table',
                        self.input()['table'].path,
                        '--i-seq',
                        self.input()['rep_seqs'].path,
                        '--o-ko-metagenome',
                        self.output()['ko_metagenome'].path,
                        '--o-ec-metagenome',
                        self.output()['ec_metagenome'].path,
                        '--o-pathway-abundance',
                        self.output()['pathway'].path,
                        '--p-threads',
                        self.threads,
                        '--p-hsp-method',
                        self.p_hsp_method,
                        '--p-max-nsti',
                        self.max_nsti,
                        '--verbose']

        log_output = run_cmd(picrust_cmd, self)

        #with self.output['log'].open('w') as fh:
        #    fh.write(log_output)

class Export_Picrust(luigi.Task):
    picrust_dir = Output_Dirs().picrust_dir
    def requires(self):
        return Picrust()

    def output(self):
        pathway = os.path.join(self.picrust_dir,
                "exported_pathway_abundance.tsv")
        ec_metagenome = os.path.join(self.picrust_dir,
                "exported_ec_metagenome.tsv")
        ko_metagenome = os.path.join(self.picrust_dir,
                "exported_ko_metagenome.tsv")

        out = {
            "pathway": luigi.LocalTarget(pathway),
            "ec_metagenome": luigi.LocalTarget(ec_metagenome),
            "ko_metagenome": luigi.LocalTarget(ko_metagenome)
        }

        return out

    def run(self):
        export_script_path = os.path.join(qiime2_helper_dir,
                "artifact_helper.py")

        pathway_command = ['python',
                    export_script_path,
                    '--artifact-path',
                    self.input()['pathway'].path,
                    '--output-path',
                    self.output()['pathway'].path]

        ec_command = ['python',
                    export_script_path,
                    '--artifact-path',
                    self.input()['ec_metagenome'].path,
                    '--output-path',
                    self.output()['ec_metagenome'].path]

        ko_command = ['python',
                    export_script_path,
                    '--artifact-path',
                    self.input()['ko_metagenome'].path,
                    '--output-path',
                    self.output()['ko_metagenome'].path]

        run_cmd(pathway_command, self)
        run_cmd(ec_command, self)
        run_cmd(ko_command, self)

# Visualizations
class Denoise_Tabulate(luigi.Task):
    samples = Samples().get_samples()
    is_multiple = str2bool(Samples().is_multiple)
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Denoise()

    def output(self):
        if(self.is_multiple):
            output = {}
            for sample in self.samples:
                out_dir = os.path.join(self.out_dir, str(sample))
                prefix = str(sample) + "_stats_dada2.qzv"
                denoise_tabulated = os.path.join(out_dir, prefix)

                output[str(sample)] = luigi.LocalTarget(denoise_tabulated)

            return output
        else:
            denoise_tabulated = os.path.join(self.out_dir, "stats_dada2.qzv")

            return luigi.LocalTarget(denoise_tabulated)

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        if(self.is_multiple):
            for sample in self.samples:
                # Make sub-output directory
                run_cmd(["mkdir",
                        '-p',
                        os.path.join(self.out_dir, str(sample))],
                        self)

                # Run qiime metadata tabulate
                cmd = ["qiime",
                        "metadata",
                        "tabulate",
                        "--m-input-file",
                        self.input()[str(sample)]["stats"].path,
                        "--o-visualization",
                        self.output()[str(sample)].path]

                run_cmd(cmd, self)
        else:
            # Run qiime metadata tabulate
            cmd = ["qiime",
                    "metadata",
                    "tabulate",
                    "--m-input-file",
                    self.input()["stats"].path,
                    "--o-visualization",
                    self.output().path]

            run_cmd(cmd, self)

class Merge_Denoise_Tabulate(luigi.Task):
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Merge_Denoise_Stats()

    def output(self):
        merged_denoise_tabulated = os.path.join(self.out_dir, "merged_stats_dada2.qzv")

        return luigi.LocalTarget(merged_denoise_tabulated)

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        cmd = ["qiime",
                "metadata",
                "tabulate",
                "--m-input-file",
                self.input()["qza"].path,
                "--o-visualization",
                self.output().path]

        run_cmd(cmd, self)


class Sequence_Tabulate(luigi.Task):
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Merge_Denoise()

    def output(self):
        sequence_tabulated = os.path.join(self.out_dir, "merged_dada2_rep_seqs.qzv")

        return luigi.LocalTarget(sequence_tabulated)

    def run(self):
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                self)

        # Run qiime metadata tabulate
        cmd = ["qiime",
                "feature-table",
                "tabulate-seqs",
                "--i-data",
                self.input()["rep_seqs"].path,
                "--o-visualization",
                self.output().path]

        run_cmd(cmd, self)

class Taxonomy_Tabulate(luigi.Task):
    out_dir = Output_Dirs().taxonomy_dir

    def requires(self):
        return Taxonomic_Classification()

    def output(self):
        tabulated = os.path.join(self.out_dir, "taxonomy.qzv")

        return luigi.LocalTarget(tabulated)

    def run(self):
        step = str(self)

        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                step)

        # Tabulate taxonomy classification result
        cmd = ["qiime",
                "metadata",
                "tabulate",
                "--m-input-file",
                self.input()["taxonomy"].path,
                "--o-visualization",
                self.output().path]

        run_cmd(cmd, step)

class Rarefaction_Curves(luigi.Task):
    sampling_depth = luigi.Parameter(default="10000")
    out_dir = Output_Dirs().visualization_dir

    def requires(self):
        return {
                'Merge_Denoise': Merge_Denoise(),
                'Phylogeny_Tree': Phylogeny_Tree()
                }

    def output(self):
        alpha_rarefaction = os.path.join(self.out_dir,
                "alpha_rarefaction_" + self.max_depth + ".qzv")

        return luigi.LocalTarget(alpha_rarefaction)

    def run(self):
        # Make directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        # If sampling depth is 0, automatically determine sampling depth
        if(self.sampling_depth == '0'):
            sampling_depth = auto_sampling_depth(self.input()['Merge_Denoise'].path)
        else:
            sampling_depth = self.sampling_depth

        # Make alpha rarefaction curve
        cmd = [
                'qiime',
                'diversity',
                'alpha-rarefaction',
                '--i-table',
                self.input()['Merge_Denoise']['table'].path,
                '--i-phylogeny',
                self.input()['Phylogeny_Tree']['rooted_tree'].path,
                '--p-max-depth',
                sampling_depth,
                '--o-visualization',
                self.output().path
                ]

        run_cmd(cmd, self)

class Alpha_Group_Significance(luigi.Task):
    out_dir = Output_Dirs().analysis_dir
    metadata_file = Samples().metadata_file

    def requires(self):
        return Core_Metrics_Phylogeny()

    def output(self):
        faith_group_significance = os.path.join(self.out_dir,
                "faith_pd_group_significance.qzv")
        evenness_group_significance = os.path.join(self.out_dir,
                "evenness_group_significance.qzv")
        shannon_group_significance = os.path.join(self.out_dir,
                "shannon_pd_group_significance.qzv")

        output = {
                'faith_pd_group_significance':
                    luigi.LocalTarget(faith_group_significance),
                'evenness_group_significance':
                    luigi.LocalTarget(evenness_group_significance),
                'shannon_group_significance':
                    luigi.LocalTarget(shannon_group_significance)
                }

        return output

    def run(self):
        # Make sure Metadata file is provided and exists
        if not(os.path.isfile(self.metadata_file)):
            msg = dedent("""
                    Metadata file is not provided or the provided Metadata file
                    does not exist!
                    """)

            raise FileNotFoundError(msg)

        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        # Keys to input and output targets
        alpha_groups = [
                ('faith_pd_vector', 'faith_pd_group_significance'),
                ('evenness_vector', 'evenness_group_significance'),
                ('shannon_vector', 'shannon_group_significance')
                ]

        for input_key, output_key in alpha_groups:
            cmd = ['qiime',
                    'diversity',
                    'alpha-group-significance',
                    '--i-alpha-diversity',
                    self.input()[input_key].path,
                    '--m-metadata-file',
                    self.metadata_file,
                    '--o-visualization',
                    self.output()[output_key].path]

            run_cmd(cmd, self)

class PCoA_Plots(luigi.Task):
    out_dir = Output_Dirs().pcoa_dir
    metadata_file = Samples().metadata_file

    def requires(self):
        return Core_Metrics_Phylogeny()

    def output(self):
        unweighted_unifrac_pcoa = os.path.join(self.out_dir,
                "unweighted_unifrac_pcoa_plots.pdf")
        weighted_unifrac_pcoa = os.path.join(self.out_dir,
                "weighted_unifrac_pcoa_plots.pdf")
        bray_curtis_pcoa = os.path.join(self.out_dir,
                "bray_curtis_pcoa_plots.pdf")
        jaccard_pcoa = os.path.join(self.out_dir,
                "jaccard_pcoa_plots.pdf")

        output = {
                'unweighted_unifrac_pcoa':
                luigi.LocalTarget(unweighted_unifrac_pcoa),
                'weighted_unifrac_pcoa':
                luigi.LocalTarget(weighted_unifrac_pcoa),
                'bray_curtis_pcoa': luigi.LocalTarget(bray_curtis_pcoa),
                'jaccard_pcoa': luigi.LocalTarget(jaccard_pcoa)
                }

        return output

    def run(self):
        # Make sure Metadata file is provided and exists
        if not(os.path.isfile(self.metadata_file)):
            msg = dedent("""
                    Metadata file is not provided or the provided Metadata file
                    does not exist!
                    """)

            raise FileNotFoundError(msg)

        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        # Input PCoA artifacts to loop through
        # (It's identical to output keys!)
        metrics = ['unweighted_unifrac_pcoa', 'weighted_unifrac_pcoa',
                'jaccard_pcoa', 'bray_curtis_pcoa']

        # Make PCoA plots for each distance metric
        pcoa_plot_script = os.path.join(script_dir, "generate_multiple_pcoa.py")
        for metric in metrics:
            outdir = os.path.dirname(self.output()[metric].path)
            filename = os.path.basename(self.output()[metric].path)

            generate_pdf(self.input()[metric].path,
                        self.metadata_file,
                        filename,
                        outdir)

class PCoA_Plots_jpeg(luigi.Task):
    out_dir = Output_Dirs().pcoa_dir
    metadata_file = Samples().metadata_file

    unweighted_unifrac_dir = os.path.join(out_dir, "unweighted_unifrac")
    weighted_unifrac_dir = os.path.join(out_dir, "weighted_unifrac")
    bray_curtis_dir = os.path.join(out_dir, "bray_curtis")
    jaccard_dir = os.path.join(out_dir, "jaccard")

    def requires(self):
        return Core_Metrics_Phylogeny()

    def output(self):
        json_summary = os.path.join(self.out_dir,
                "pcoa_columns.json")

        return luigi.LocalTarget(json_summary)

    def run(self):
        # Make sure Metadata file is provided and exists
        if not(os.path.isfile(self.metadata_file)):
            msg = dedent("""
                    Metadata file is not provided or the provided Metadata file
                    does not exist!
                    """)

            raise FileNotFoundError(msg)

        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        # Input PCoA artifacts to loop through
        # (It's identical to output keys!)
        metrics_outdir_map = {
            'unweighted_unifrac_pcoa': self.unweighted_unifrac_dir,
            'weighted_unifrac_pcoa': self.weighted_unifrac_dir,
            'jaccard_pcoa': self.jaccard_dir,
            'bray_curtis_pcoa': self.bray_curtis_dir,
        }

        # Make PCoA plots for each distance metric
        for metric in metrics_outdir_map:
            outdir = metrics_outdir_map[metric]

            # Make sub-output directory
            run_cmd(['mkdir',
                    '-p',
                    outdir],
                    self)

            generate_images(
                    self.input()[metric].path,
                    self.metadata_file,
                    outdir
            )

        save_as_json(self.metadata_file, self.output().path)

# Get software version info
class Get_Version_Info(luigi.Task):
    out_dir = Output_Dirs().out_dir

    def output(self):
        version_info = os.path.join(self.out_dir, "version_info.txt")

        return luigi.LocalTarget(version_info)

    def run(self):
        # Make output directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                self)

        # Get QIIME2 Version information
        info = run_cmd(['qiime',
                        'info'],
                        self)

        classifier_path = Taxonomic_Classification().classifier

        with self.output().open('w') as fh:
            fh.write(info.decode('utf-8'))
            fh.write('\n\n')
            fh.write('Taxonomic Classifier path\n')
            fh.write(classifier_path)

# Dummy Class to run multiple tasks
class Core_Analysis(luigi.Task):
    out_dir = Output_Dirs().out_dir

    def requires(self):
        return [
                Summarize(),
                Generate_Combined_Feature_Table(),
                Phylogeny_Tree(),
                Denoise_Tabulate(),
                Sample_Count_Summary(),
                Sequence_Tabulate(),
                Taxonomy_Tabulate(),
                Export_Taxa_Collapse(),
                Get_Version_Info(),
                ]

    def output(self):
        return luigi.LocalTarget(os.path.join(self.out_dir, "core_analysis_done"))

    def run(self):
        with self.output().open('w') as fh:
            fh.write("Done!")

class Post_Analysis(luigi.Task):
    def requires(self):
        return [
                Core_Analysis(),
                Summarize_Filtered_Table(),
                Generate_Combined_Filtered_Feature_Table(),
                Core_Metrics_Phylogeny(),
                Alpha_Group_Significance(),
                Generate_Combined_Rarefied_Feature_Table(),
                PCoA_Plots(),
                Get_Version_Info()
        ]

# Dummy class to run Input Upload tasks
class Run_Input_Upload_Tasks(luigi.Task):

    def requires(self):
        return [
            Import_Data(),
            Summarize(),
            Get_Version_Info()
        ]

# Dummy class to run Denoise tasks
class Run_Denoise_Tasks(luigi.Task):

    def requires(self):
        return [
            Denoise(),
            Merge_Denoise(),
            Merge_Denoise_Stats(),
            Sample_Count_Summary(),
            Denoise_Tabulate(),
            Merge_Denoise_Tabulate(),
            Get_Version_Info(),
        ]

class Run_TaxonomicClassification_Tasks(luigi.Task):
    """
    Run all the steps involved in the 'Taxonomic Classification module'

    Input:
        Merge_Denoise()
    """
    def requires(self):
        return [
            Taxonomic_Classification(),
            Export_Taxonomy(),
            Taxa_Collapse(),
            Export_Taxa_Collapse(),
            Get_Version_Info(),
        ]

class Run_Analysis_Tasks(luigi.Task):
    """
    Run all the steps involved in the 'Analysis module'

    Input:
        Merge_Denoise()
        Taxonomic_Classification()
    """
    def requires(self):
        return [
            Export_Representative_Seqs(),
            Generate_Combined_Feature_Table(),
            Phylogeny_Tree(),
            Filter_Feature_Table(),
            Core_Metrics_Phylogeny(),
            PCoA_Plots(),
            PCoA_Plots_jpeg(),
            Get_Version_Info(),
        ]

if __name__ == '__main__':
    luigi.run()
