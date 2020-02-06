# Add parent directory to path
import sys
sys.path.append('../..')
# Unit test modules
import unittest
from unittest import mock
from textwrap import dedent
import os

from generate_manifest import *

def Create_fastq():
    SAMPLE_NAME = 1

    mockfiles = []
    # Create 3 empty files with fastq.gz extensions
    for i in range(0, 3):
        s_name = str(SAMPLE_NAME)

        forward_fastq = s_name + "_S" + s_name + "_L001_R1_001.fastq.gz"
        reverse_fastq = s_name + "_S" + s_name + "_L001_R2_001.fastq.gz"

        mockfiles.append(forward_fastq)
        mockfiles.append(reverse_fastq)

        SAMPLE_NAME = SAMPLE_NAME + 1

    return mockfiles

class Check_Manifest(unittest.TestCase):
    GOOD_DATA = dedent("""
            [Header],,,,,,,,,
            IEMFileVersion,4,,,,,,,,
            Investigator Name,Katja Engel,,,,,,,,
            [Reads],,,,,,,,,
            251,,,,,,,,,
            251,,,,,,,,,
            [Data],,,,,,,,,
            Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description
            DD1,1,nested,A1,V4-R1,ATCACG,Pro341Fi1,TCTCGG,,
            special1,xx1,nested,C5,V4-R11,GGCTAC,Pro341Fi2,TGTGCC,,
            DD2,2,nested,A2,V4-R9,GATCAG,Pro341Fi1,TCTCGG,,
            DD4,4,nested,A4,V4-R1,ATCACG,Pro341Fi2,TGTGCC,,
            """).strip()

    EMPTY_DATA = dedent("""
            [Header],,,,,,,,,
            IEMFileVersion,4,,,,,,,,
            Investigator Name,Katja Engel,,,,,,,,
            [Reads],,,,,,,,,
            251,,,,,,,,,
            251,,,,,,,,,
            [Data],,,,,,,,,
            Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description
            """).strip()

    @mock.patch("generate_manifest.os.path")
    def test_samplesheet(self, mock_path):
        mock_path.isfile.return_value = False

        # Make sure it throws an error if file is not found
        with self.assertRaises(FileNotFoundError):
            read_samplesheet(mock_path)

        # Check for empty data
        mock_path.isfile.return_value = True
        data = mock.mock_open(read_data=self.EMPTY_DATA)
        data.return_value.__iter__ = lambda self: self
        data.return_value.__next__ = lambda self: next(iter(self.readline, ''))
        with mock.patch('builtins.open', data) as m:
            with self.assertRaises(ValueError):
                read_samplesheet("mocked/samplesheet.csv")

        # Check if working as intended
        expected = {
                '1': 'DD1',
                'xx1': 'special1',
                '2': 'DD2',
                '4': 'DD4'
                }

        mock_path.isfile.return_value = True
        data = mock.mock_open(read_data=self.GOOD_DATA)
        data.return_value.__iter__ = lambda self: self
        data.return_value.__next__ = lambda self: next(iter(self.readline, ''))
        with mock.patch('builtins.open', data) as m:
            obs = read_samplesheet("mocked/samplesheet.csv")

            self.assertEqual(obs, expected)

    @mock.patch("generate_manifest.os.listdir")
    @mock.patch("generate_manifest.os.path.isdir")
    @mock.patch("generate_manifest.os.path.isfile")
    def test_data_directory(self, mock_isfile, mock_isdir, mock_listdir):
        mock_isdir.return_value = False
        mock_isfile.return_value = True

        # Check non-existent directory handling
        with self.assertRaises(FileNotFoundError):
            generate_manifest("mock_file", "/mock_dir")


        # Check for normal case
        mock_isdir.return_value = True
        mock_listdir.return_value = Create_fastq()
        expected = {
                '1': 'DD1',
                'xx1': 'special1',
                '2': 'DD2',
                '4': 'DD4'
                }

        manifest_lines, excluded_files, missing_files = \
                generate_manifest(expected, "mock_dir")

        # Same manifest lines
        expected_manifest = [
                'DD1,' + os.path.abspath('mock_dir/1_S1_L001_R1_001.fastq.gz')\
                        + ',forward',
                'DD1,' + os.path.abspath('mock_dir/1_S1_L001_R2_001.fastq.gz')\
                        + ',reverse',
                'DD2,' + os.path.abspath('mock_dir/2_S2_L001_R1_001.fastq.gz')\
                        + ',forward',
                'DD2,' + os.path.abspath('mock_dir/2_S2_L001_R2_001.fastq.gz')\
                        + ',reverse'
                ]

        self.assertEqual(manifest_lines, expected_manifest)

        # Same excluded files
        expected_excluded_files = [
                '3_S3_L001_R1_001.fastq.gz',
                '3_S3_L001_R2_001.fastq.gz']

        self.assertEqual(
                sorted(excluded_files),
                sorted(expected_excluded_files)
        )

        # Same missing files
        expected_missing_files = [
                '4_S4_L001_R1_001.fastq.gz',
                '4_S4_L001_R2_001.fastq.gz',
                'xx1_Sxx1_L001_R1_001.fastq.gz',
                'xx1_Sxx1_L001_R2_001.fastq.gz',
                ]

        self.assertEqual(
                sorted(missing_files),
                sorted(expected_missing_files)
        )

if __name__ == '__main__':
    unittest.main()
