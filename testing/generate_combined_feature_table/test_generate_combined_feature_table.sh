#!/usr/bin/env bash
set -euo pipefail
# test_generate_combined_feature_table.sh
# Copyright Jackson M. Tsuji, 2019
# End-to-end test for generate_combined_feature_table.py

# GLOBAL variables
readonly SCRIPT_NAME="${0##*/}"
FAILED_TESTS=0

#### FUNCTIONS
#######################################
# Compares two MD5 hashes for the same file in HARD-CODED output dirs
# Globals:
#   FAILED_TESTS: count of failed tests
# Arguments:
#   input_basename: the basename (no directory, no extension) of the desired MD5 hashes to test between the outputs and expected_outputs folders
# Returns:
#   updates FAILED_TESTS
#######################################
function check_md5s() {
  # User-provided inputs
  local input_basename
  input_basename=$1

  # TODO - maybe set output and expected_outputs dirs as GLOBAL
  md5_expected=$(cat "${expected_outputs_dir}/${input_basename}.tsv.md5" | cut -d " " -f 1)
  md5_actual=$(cat "${output_dir}/${input_basename}.tsv.md5" | cut -d " " -f 1)

  if [[ "${md5_expected}" != "${md5_actual}" ]]; then
    echo "[ $(date -u) ]: '${input_basename}.tsv': FAILED: Actual hash does not match expected hash"
    FAILED_TESTS=$((${FAILED_TESTS}+1))
  else
    echo "[ $(date -u) ]: '${input_basename}.tsv': PASSED"
  fi
}
##########

# If no input is provided, provide help and exit
if [[ $# -eq 0 ]]; then
  echo "No arguments provided. Please run '-h' or '--help' to see help. Exiting..." >&2
  exit 1
elif [[ $1 = "-h" ]] || [[ $1 = "--help" ]]; then

  # Help statement
  printf "${SCRIPT_NAME}: run end-to-end test for generate_combined_feature_table.py\n"
  printf "Copyright Jackson M. Tsuji, Neufeld Research Group, 2019\n\n"
  printf "Usage: ${SCRIPT_NAME} test_dir\n\n"
  printf "Positional arguments (required):\n"
  printf "   test_dir: path to the test directory containing the 'inputs' and 'outputs_expected' test folders\n\n"
  printf "Note: script will give an exit status of 1 if any tests fail; otherwise exit status will be 0.\n\n"

  # Exit
  exit 0
fi

### Get user inputs
test_dir=$1

echo "[ $(date -u) ]: Running ${SCRIPT_NAME}"
echo "[ $(date -u) ]: Test dir: '${test_dir}'"

### Expected positions of folders
input_dir="${test_dir}/inputs"
expected_outputs_dir="${test_dir}/outputs_expected"
output_dir="${test_dir}/outputs" # should NOT yet exist!

### Look for dirs
if [[ ! -d "${input_dir}" ]]; then
  echo "[ $(date -u) ]: ERROR: did not find input dir at '${input_dir}'. Exiting..."
  exit 1
elif [[ ! -d "${expected_outputs_dir}" ]]; then
  echo "[ $(date -u) ]: ERROR: did not find expected outputs dir at '${expected_outputs_dir}'. Exiting..."
  exit 1
fi

### Create the output dir
if [[ -d "${output_dir}" ]]; then
  echo "[ $(date -u) ]: ERROR: output directory '${output_dir}' already exists. Please specify an output dir that does not exist. Exiting..."
  exit 1
else
  mkdir "${output_dir}"
fi

## Test 1
test_ID="01_standard"
echo "[ $(date -u) ]: Running script on test data '${test_ID}'"
generate_combined_feature_table.py \
  -f "${input_dir}/feature_table.tsv" \
  -s "${input_dir}/representative_seqs.fasta" \
  -t "${input_dir}/taxonomy.tsv" \
  -o "${output_dir}/${test_ID}.tsv" \
  > "${output_dir}/${test_ID}.log" 2>&1
# TODO - print an error message if this fails

# Generate MD5 hash on expected output
cat "${output_dir}/${test_ID}.tsv" | md5sum > "${output_dir}/${test_ID}.tsv.md5"

# Compare
check_md5s "${test_ID}"

## Test 2
test_ID="02_renamed"
echo "[ $(date -u) ]: Running script on test data '${test_ID}'"
generate_combined_feature_table.py \
  -f "${input_dir}/feature_table.tsv" \
  -s "${input_dir}/representative_seqs.fasta" \
  -t "${input_dir}/taxonomy.tsv" \
  -o "${output_dir}/${test_ID}.tsv" \
  -N "#OTU ID" \
  -R \
  > "${output_dir}/${test_ID}.log" 2>&1
# TODO - print an error message if this fails

# Generate MD5 hash on expected output
cat "${output_dir}/${test_ID}.tsv" | md5sum > "${output_dir}/${test_ID}.tsv.md5"

# Compare
check_md5s "${test_ID}"

## Test 3
test_ID="03_simple"
echo "[ $(date -u) ]: Running script on test data '${test_ID}'"
generate_combined_feature_table.py \
  -f "${input_dir}/feature_table.tsv" \
  -N "#OTU ID" \
  -R \
  > "${output_dir}/${test_ID}.tsv" \
  2> "${output_dir}/${test_ID}.log"
# TODO - print an error message if this fails

# Generate MD5 hash on expected output
cat "${output_dir}/${test_ID}.tsv" | md5sum > "${output_dir}/${test_ID}.tsv.md5"

# Compare
check_md5s "${test_ID}"

## Test 4 - parsed taxonomy
test_ID="04_parsed"
echo "[ $(date -u) ]: Running script on test data '${test_ID}'"
generate_combined_feature_table.py \
  -f "${input_dir}/feature_table.tsv" \
  -s "${input_dir}/representative_seqs.fasta" \
  -t "${input_dir}/taxonomy.tsv" \
  -o "${output_dir}/${test_ID}.tsv" \
  -P \
  > "${output_dir}/${test_ID}.log" 2>&1
# TODO - print an error message if this fails

# Generate MD5 hash on expected output
cat "${output_dir}/${test_ID}.tsv" | md5sum > "${output_dir}/${test_ID}.tsv.md5"

# Compare
check_md5s "${test_ID}"

### Overall status
if [[ "${FAILED_TESTS}" -eq 0 ]]; then
  echo "[ $(date -u) ]: All tests PASSED. Deleting output folder."
  rm -r "${output_dir}"
  echo "[ $(date -u) ]: Testing complete."
  exit 0
else
  echo "[ $(date -u) ]: ${FAILED_TESTS} test(s) FAILED. See above log for details. Keeping outputs dir for reference. Testing complete."
  exit 1
fi
