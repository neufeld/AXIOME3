import luigi
import os
import sys
#from subprocess import check_output, CalledProcessError
import subprocess
import logging

# Define custom logger
logger = logging.getLogger("custom logger")

# Path to configuration file to be used
luigi.configuration.add_config_path("configuration/luigi.cfg")

# Color formatter
formatters = {
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'END': '\033[0m'
        }

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
                "resulted in an error:\n{RED}{combined_msg}{END}"\
                        .format(combined_msg=combined_msg,
                                RED=formatters['RED'],
                                END=formatters['END'])


        logger.error(err_msg)
        raise ValueError(err_msg)
    else:
        return stdout

class Out_Prefix(luigi.Config):
    prefix = luigi.Parameter()

class Output_Dirs(luigi.Config):
    # Define output paths
    out_dir = Out_Prefix().prefix
    denoise_dir = os.path.join(out_dir, "dada2")
    rarefy_dir = os.path.join(out_dir, "rarefy")
    taxonomy_dir = os.path.join(out_dir, "taxonomy")
    export_dir = os.path.join(out_dir, "exported")
    rarefy_export_dir = os.path.join(out_dir, "rarefy_exported")
    phylogeny_dir = os.path.join(out_dir, "phylogeny")
    core_metric_dir = os.path.join(out_dir, "core_div_phylogeny")
    visualization_dir = os.path.join(out_dir, "visualization")

class Samples(luigi.Config):
    """
    Global variables that multiple steps may need access to.
    Includes...
        1. Manifest file (.txt) (maybe only accept .txt extension?)

    """
    manifest_file = luigi.Parameter()
    metadata_file = luigi.Parameter(default='')

class Import_Data(luigi.Task):
    # Options for qiime tools import
    sample_type = luigi.Parameter(
            default='SampleData[PairedEndSequencesWithQuality]')
    input_format = luigi.Parameter(default="PairedEndFastqManifestPhred33")

    def output(self):
        paired_end_demux = os.path.join(Output_Dirs().out_dir, "paired-end-demux.qza")

        return luigi.LocalTarget(paired_end_demux)

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(['mkdir',
                '-p',
                Output_Dirs().out_dir],
                self)

        inputPath = Samples().manifest_file

        # Make sure input file actually exists
        try:
            with open(inputPath, 'r') as fh:
                fh.readlines()
        except FileNotFoundError:
            logger.error("Input file for qiime tools import does not exist...")
            sys.exit(1)
        # in case of unexpected errors
        except Exception as err:
            logger.error(
            "In Import_Data() following error occured\n" + str(err))
            raise

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

        output = run_cmd(cmd, self)

class Summarize(luigi.Task):

    def requires(self):
        return Import_Data()

    def output(self):
        summary_file = os.path.join(Output_Dirs().out_dir, "paired-end-demux.qzv")

        return luigi.LocalTarget(summary_file)

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().out_dir],
                step)

        # Generate summary file
        cmd = ["qiime",
                "demux",
                "summarize",
                "--i-data",
                self.input().path,
                "--o-visualization",
                self.output().path]

        run_cmd(cmd, step)

class Denoise(luigi.Task):
    trim_left_f = luigi.Parameter(default="19")
    trunc_len_f = luigi.Parameter(default="250")
    trim_left_r = luigi.Parameter(default="20")
    trunc_len_r = luigi.Parameter(default="250")
    n_threads = luigi.Parameter(default="10")

    def requires(self):
        return Import_Data()

    def output(self):
        denoise_table = os.path.join(Output_Dirs().denoise_dir, "dada2-table.qza")
        rep_seqs = os.path.join(Output_Dirs().denoise_dir, "dada2-rep-seqs.qza")
        denoise_stats = os.path.join(Output_Dirs().denoise_dir, "stats-dada2.qza")
        dada2_log = os.path.join(Output_Dirs().denoise_dir, "dada2_log.txt")

        out = {
                "table": luigi.LocalTarget(denoise_table),
                "rep_seqs": luigi.LocalTarget(rep_seqs),
                "stats": luigi.LocalTarget(denoise_stats),
                "log": luigi.LocalTarget(dada2_log, format=luigi.format.Nop)
                }

        return out

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().denoise_dir],
                step)

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
                self.n_threads,
                "--o-table",
                self.output()["table"].path,
                "--o-representative-sequences",
                self.output()["rep_seqs"].path,
                "--o-denoising-stats",
                self.output()["stats"].path,
                "--verbose"]

        output = run_cmd(cmd, step)

        # Write a log file
        with self.output()["log"].open('wb') as fh:
            fh.write(output)

class Rarefy(luigi.Task):
    sampling_depth = luigi.Parameter(default="10000")

    def requires(self):
        return Denoise()

    def output(self):
        rarefied_table = os.path.join(Output_Dirs().rarefy_dir,
                "rarefied_table.qza")

        return luigi.LocalTarget(rarefied_table)

    def run(self):
        step = str(self)

        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().rarefy_dir],
                step)

        # Rarefy
        cmd = ["qiime",
                "feature-table",
                "rarefy",
                "--i-table",
                self.input()['table'].path,
                "--p-sampling-depth",
                self.sampling_depth,
                "--o-rarefied-table",
                self.output().path
                ]
        run_cmd(cmd, step)

class Taxonomic_Classification(luigi.Task):
    classifier = luigi.Parameter()
    n_jobs = luigi.Parameter(default="10")

    def requires(self):
        return Denoise()

    def output(self):
        classified_taxonomy = os.path.join(Output_Dirs().taxonomy_dir, "taxonomy.qza")
        taxonomy_log = os.path.join(Output_Dirs().taxonomy_dir, "taxonomy_log.txt")

        output = {
                "taxonomy": luigi.LocalTarget(classified_taxonomy),
                "log": luigi.LocalTarget(taxonomy_log, format=luigi.format.Nop)
                }

        return output

    def run(self):
        step = str(self)

        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().taxonomy_dir],
                step)

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
                self.n_jobs,
                "--verbose"]

        output = run_cmd(cmd, step)

        # Log result
        with self.output()["log"].open('wb') as fh:
            fh.write(output)

class Export_Feature_Table(luigi.Task):

    def requires(self):
        return Denoise()

    def output(self):
        biom = os.path.join(Output_Dirs().export_dir, "feature-table.biom")

        return luigi.LocalTarget(biom)

    def run(self):
        step = str(self)
        # Make directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().export_dir],
                step)

        # Export file
        cmd = ["qiime",
                "tools",
                "export",
                "--input-path",
                self.input()["table"].path,
                "--output-path",
                os.path.dirname(self.output().path)]

        run_cmd(cmd, step)

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

class Export_Taxonomy(luigi.Task):

    def requires(self):
        return Taxonomic_Classification()

    def output(self):
        tsv = os.path.join(Output_Dirs().export_dir, "taxonomy.tsv")

        return luigi.LocalTarget(tsv)

    def run(self):
        step = str(self)
        # Make directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().export_dir],
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

    def requires(self):
        return Denoise()

    def output(self):
        fasta = os.path.join(Output_Dirs().export_dir, "dna-sequences.fasta")

        return luigi.LocalTarget(fasta)

    def run(self):
        step = str(self)
        # Make directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().export_dir],
                step)

        # Export file
        cmd = ["qiime",
                "tools",
                "export",
                "--input-path",
                self.input()["rep_seqs"].path,
                "--output-path",
                os.path.dirname(self.output().path)]

        run_cmd(cmd, step)

class Convert_Biom_to_TSV(luigi.Task):

    def requires(self):
        return Export_Feature_Table()

    def output(self):
        tsv = os.path.join(Output_Dirs().export_dir, "feature-table.tsv")

        return luigi.LocalTarget(tsv)

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().export_dir],
                step)

        # Convert to TSV
        cmd = ["biom",
                "convert",
                "-i",
                self.input().path,
                "-o",
                self.output().path,
                "--to-tsv"]

        run_cmd(cmd, step)

class Convert_Rarefy_Biom_to_TSV(luigi.Task):

    def requires(self):
        return Export_Rarefy_Feature_Table()

    def output(self):
        tsv = os.path.join(Output_Dirs().rarefy_export_dir, "feature-table.tsv")

        return luigi.LocalTarget(tsv)

    def run(self):
        step = str(self)
        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().rarefy_export_dir],
                step)

        # Convert to TSV
        cmd = ["biom",
                "convert",
                "-i",
                self.input().path,
                "-o",
                self.output().path,
                "--to-tsv"]

        run_cmd(cmd, step)

class Generate_Combined_Feature_Table(luigi.Task):

    def requires(self):
        return {
                "Export_Taxonomy": Export_Taxonomy(),
                "Export_Representative_Seqs": Export_Representative_Seqs(),
                "Convert_Biom_to_TSV": Convert_Biom_to_TSV(),
                "Convert_Rarefy_Biom_to_TSV": Convert_Rarefy_Biom_to_TSV()
                }

    def output(self):
        combined_table = os.path.join(Output_Dirs().export_dir, "ASV_table_combined.tsv")
        log = os.path.join(Output_Dirs().export_dir, "ASV_table_combined.log")

        combined_rarefied_table = os.path.join(Output_Dirs().rarefy_export_dir,
                "ASV_rarefied_table_combined.tsv")
        rarefied_log = os.path.join(Output_Dirs().rarefy_export_dir,
                "ASV_rarefied_table_combined.log")

        output = {
                "table": luigi.LocalTarget(combined_table),
                "log": luigi.LocalTarget(log, format=luigi.format.Nop),
                "rarefied_table": luigi.LocalTarget(combined_rarefied_table),
                "rarefied_log": luigi.LocalTarget(rarefied_log,
                    format=luigi.format.Nop)
                }

        return output

    def run(self):
        step = str(self)

        # Make output directory
        run_cmd(["mkdir",
                "-p",
                Output_Dirs().export_dir],
                step)

        # Run Jackson's script on pre-rarefied table
        cmd_pre_rarefied = ["generate_combined_feature_table.py",
                "-f",
                self.input()["Convert_Biom_to_TSV"].path,
                "-s",
                self.input()["Export_Representative_Seqs"].path,
                "-t",
                self.input()["Export_Taxonomy"].path,
                "-o",
                self.output()["table"].path]

        logged_pre_rarefied = run_cmd(cmd_pre_rarefied, step)

        # Run Jackson's script on rarefied table
        cmd_rarefied = ["generate_combined_feature_table.py",
                "-f",
                self.input()["Convert_Rarefy_Biom_to_TSV"].path,
                "-s",
                self.input()["Export_Representative_Seqs"].path,
                "-t",
                self.input()["Export_Taxonomy"].path,
                "-o",
                self.output()["rarefied_table"].path]

        logged_rarefied = run_cmd(cmd_rarefied, step)

        # Write log files
        with self.output()["log"].open('w') as fh:
            fh.write(logged_pre_rarefied)

        with self.output()["rarefied_log"].open('w') as fh:
            fh.write(logged_rarefied)

# Post Analysis
class Phylogeny_Tree(luigi.Task):

    def requires(self):
        return Denoise()

    def output(self):
        alignment = os.path.join(Output_Dirs().phylogeny_dir,
                "aligned_rep_seqs.qza")
        masked_alignment = os.path.join(Output_Dirs().phylogeny_dir,
                "masked_aligned_rep_seqs.qza")
        tree = os.path.join(Output_Dirs().phylogeny_dir,
                "unrooted_tree.qza")
        rooted_tree = os.path.join(Output_Dirs().phylogeny_dir,
                "rooted_tree.qza")

        out = {
            'alignment': luigi.LocalTarget(alignment),
            'masked_alignment': luigi.LocalTarget(masked_alignment),
            'tree': luigi.LocalTarget(tree),
            'rooted_tree': luigi.LocalTarget(rooted_tree),
        }

        return out

    def run(self):
        step = str(self)

        # Create output directory
        run_cmd(['mkdir',
                '-p',
                Output_Dirs().phylogeny_dir], step)

        # Make phylogeny tree
        cmd = ['qiime',
                'phylogeny',
                'align-to-tree-mafft-fasttree',
                '--i-sequences',
                self.input()['rep_seqs'].path,
                '--o-alignment',
                self.output()['alignment'].path,
                '--o-masked-alignment',
                self.output()['masked_alignment'].path,
                '--o-tree',
                self.output()['tree'].path,
                '--o-rooted-tree',
                self.output()['rooted_tree'].path
        ]

        run_cmd(cmd, step)

class Core_Metrics_Phylogeny(luigi.Task):
    sampling_depth = luigi.Parameter(default="10000")

    def requires(self):
        return {
                'Denoise': Denoise(),
                'Phylogeny_Tree': Phylogeny_Tree()
                }

    def output(self):
        out_dir = Output_Dirs().core_metric_dir

        rarefied_table = os.path.join(out_dir, "rarefied_table.qza")
        faith_pd_vector = os.path.join(out_dir, "alpha_faith_pd.qza")
        obs_otu_vector = os.path.join(out_dir, "alpha_observed_otus.qza")
        shannon_vector = os.path.join(out_dir, "alpha_shannon.qza")
        evenness_vector = os.path.join(out_dir, "alpha_evenness.qza")
        unweighted_unifrac_dist_matrix = os.path.join(out_dir,
                "unweighted_unifrac_distance.qza")
        weighted_unifrac_dist_matrix = os.path.join(out_dir,
                "weighted_unifrac_distance.qza")
        jaccard_dist_matrix = os.path.join(out_dir, "jaccard_distance.qza")
        bray_curtis_dist_matrix = os.path.join(out_dir,
                "bray_curtis_distance.qza")
        unweighted_unifrac_pcoa = os.path.join(out_dir,
                "unweighted_unifrac_pcoa.qza")
        weighted_unifrac_pcoa = os.path.join(out_dir,
                "weighted_unifrac_pcoa.qza")
        jaccard_pcoa = os.path.join(out_dir, "jaccard_pcoa.qza")
        bray_curtis_pcoa = os.path.join(out_dir, "bray_curtis_pcoa.qza")
        unweighted_unifrac_emperor = os.path.join(out_dir,
                "unweighted_unifrac_emperor.qzv")
        weighted_unifrac_emperor = os.path.join(out_dir,
                "weighted_unifrac_emperor.qzv")
        jaccard_emperor = os.path.join(out_dir, "jaccard_emperor.qzv")
        bray_curtis_emperor = os.path.join(out_dir, "bray_curtis_emperor.qzv")

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
        step = str(self)

        # Create output directory
        run_cmd(['mkdir',
                '-p',
                Output_Dirs().core_metric_dir],
                step)

        # Run core-metric-phylogenetic
        cmd = [
                'qiime',
                'diversity',
                'core-metrics-phylogenetic',
                '--i-table',
                self.input()['Denoise']['table'].path,
                '--i-phylogeny',
                self.input()['Phylogeny_Tree']['rooted_tree'].path,
                '--p-sampling-depth',
                self.sampling_depth,
                '--o-rarefied-table',
                self.output()['rarefied_table'].path,
                '--o-faith-pd-vector',
                self.output()['faith_pd_vector'].path,
                '--o-observed-otus-vector',
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

        run_cmd(cmd, step)

# Visualizations
class Denoise_Tabulate(luigi.Task):
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Denoise()

    def output(self):
        denoise_tabulated = os.path.join(self.out_dir, "stats-dada2.qzv")

        return luigi.LocalTarget(denoise_tabulated)

    def run(self):
        step = str(self)

        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                step)

        # Run qiime metadata tabulate
        cmd = ["qiime",
                "metadata",
                "tabulate",
                "--m-input-file",
                self.input()["stats"].path,
                "--o-visualization",
                self.output().path]

        run_cmd(cmd, step)

class Sequence_Tabulate(luigi.Task):
    out_dir = Output_Dirs().denoise_dir

    def requires(self):
        return Denoise()

    def output(self):
        sequence_tabulated = os.path.join(self.out_dir, "dada2_rep_seqs.qzv")

        return luigi.LocalTarget(sequence_tabulated)

    def run(self):
        step = str(self)

        # Make output directory
        run_cmd(["mkdir",
                "-p",
                self.out_dir],
                step)

        # Run qiime metadata tabulate
        cmd = ["qiime",
                "feature-table",
                "tabulate-seqs",
                "--i-data",
                self.input()["rep_seqs"].path,
                "--o-visualization",
                self.output().path]

        run_cmd(cmd, step)

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
    max_depth = luigi.Parameter(default="10000")
    out_dir = Output_Dirs().visualization_dir

    def requires(self):
        return {
                'Denoise': Denoise(),
                'Phylogeny_Tree': Phylogeny_Tree()
                }

    def output(self):
        alpha_rarefaction = os.path.join(self.out_dir,
                "alpha_rarefaction_" + self.max_depth + ".qzv")

        return luigi.LocalTarget(alpha_rarefaction)

    def run(self):
        step = str(self)
        # Make directory
        run_cmd(['mkdir',
                '-p',
                self.out_dir],
                step)

        # Make alpha rarefaction curve
        cmd = [
                'qiime',
                'diversity',
                'alpha-rarefaction',
                '--i-table',
                self.input()['Denoise']['table'].path,
                '--i-phylogeny',
                self.input()['Phylogeny_Tree']['rooted_tree'].path,
                '--p-max-depth',
                self.max_depth,
                '--o-visualization',
                self.output().path
                ]

        run_cmd(cmd, step)

class Run_All(luigi.Task):
    def requires(self):
        return [
                Import_Data(),
                Summarize(),
                Denoise(),
                Denoise_Tabulate(),
                Rarefy(),
                Taxonomic_Classification(),
                Taxonomy_Tabulate(),
                Export_Feature_Table(),
                Export_Rarefy_Feature_Table(),
                Export_Taxonomy(),
                Export_Representative_Seqs(),
                Convert_Biom_to_TSV(),
                Convert_Rarefy_Biom_to_TSV(),
                Generate_Combined_Feature_Table(),
                Core_Metrics_Phylogeny()
                ]

if __name__ == '__main__':
    luigi.run()
