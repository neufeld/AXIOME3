#!/usr/bin/env bash
# generate_manifest_template.sh
# Copyright Jackson M. Tsuji, Neufeld Research Group, 2019
# Creates a template manifest file for QIIME2 based on directory structure
# Part of the AXIOME3 project

SCRIPT_NAME=${0##*/}
SCRIPT_VERSION="0.8.0"

# Print help statement
if [[ $# -lt 1 ]]; then
  echo "Incorrect number of arguments provided. Please run '-h' or '--help' to see help. Exiting..." >&2
  exit 1
elif [[ $1 = "-h" ]] || [[ $1 = "--help" ]]; then
  printf "${SCRIPT_NAME}: Creates a template manifest file for QIIME2 based on directory structure.\n"
  printf "Version: ${SCRIPT_VERSION}\n"
  printf "Copyright Jackson M. Tsuji, Neufeld Research Group, 2019\n\n"
  printf "Usage: ${SCRIPT_NAME} folder_1 folder_2 ... folder_N > manifest.tsv\n\n"
  printf "Note: log information is printed to STDERR.\n\n"
  exit 0
fi

# Get input from user
# TODO - ignore whitespaces
input_dirs=(${@})

# Startup message
echo "[ $(date -u) ]: Running ${SCRIPT_NAME}" >&2
echo "[ $(date -u) ]: Version: ${SCRIPT_VERSION}" >&2
echo "[ $(date -u) ]: Command: ${SCRIPT_NAME} ${@}" >&2
echo "[ $(date -u) ]: Parsing samples from ${#input_dirs[@]} input directories" >&2

# Start output file
printf "sample-id\tforward-absolute-filepath\treverse-absolute-filepath\trun_ID\n"

for dir_num in $(seq 1 ${#input_dirs[@]}); do

  # Get variables
  input_dir=${input_dirs[$((${dir_num}-1))]}
  run_ID="run_${dir_num}"

  # Detect R1 read nomenclature
  length_type1=$(find "${input_dir}" -maxdepth 1 -type f -iname "*R1.fastq.gz" | wc -l)
  length_type2=$(find "${input_dir}" -maxdepth 1 -type f -iname "*R1_001.fastq.gz" | wc -l)

  if [[ ${length_type1} = 0 ]] && [[ ${length_type2} -gt 0 ]]; then
    echo "[ $(date -u) ]: Detected extension type '*R*_001.fastq.gz' in folder '${input_dir}'" >&2
    extension="_001.fastq.gz"
  elif [[ ${length_type1} -gt 0 ]] && [[ ${length_type2} = 0 ]]; then
    echo "[ $(date -u) ]: Detected extension type '*R*.fastq.gz' in folder '${input_dir}'" >&2
    extension=".fastq.gz"
  elif [[ ${length_type1} = 0 ]] && [[ ${length_type2} = 0 ]]; then
    echo "[ $(date -u) ]: ERROR: no input files detected in folder '${input_dir}'. Exiting..." >&2
    exit 1
  elif [[ ${length_type1} -gt 0 ]] && [[ ${length_type2} -gt 0 ]]; then
    echo "[ $(date -u) ]: ERROR: cannot determine a consistent rule to decide between R1 vs. R2 read names in folder '${input_dir}'. Exiting..." >&2
    exit 1
  else
    echo "[ $(date -u) ]: ERROR: cannot parse R1/R2 names in '${input_dir}'. Exiting..." >&2
    exit 1
  fi

  # Find all R1 reads
  R1_reads=($(find "${input_dir}" -maxdepth 1 -type f -iname "*R1${extension}" | sort -h))

  echo "[ $(date -u) ]: Directory '${input_dir}' ('${run_ID}'): detected ${#R1_reads[@]} samples" >&2

  # Parse out sample ID and R2 ID
  for R1_read in ${R1_reads[@]}; do

    R1_read=$(realpath ${R1_read})
    R2_read="${R1_read%_R1${extension}}_R2${extension}"
    sample_ID="${R1_read##*/}"
    sample_ID="${sample_ID%_R1${extension}}"

    if [[ ! -f "${R2_read}" ]]; then
      echo "[ $(date -u) ]: ERROR: cannot find expected R2 file '${R2_read}'. Exiting..." >&2
      exit 1
    fi

    # Write to STDOUT
    printf "${sample_ID}\t${R1_read}\t${R2_read}\t${run_ID}\n"

  done
done

echo "[ $(date -u) ]: ${SCRIPT_NAME}: Finished." >&2

