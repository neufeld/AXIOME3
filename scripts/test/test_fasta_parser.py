"""
For Python3 and above.
"""
from qiime2_helper.fasta_parser import (
        get_id_and_seq
)
from textwrap import dedent
import unittest
from unittest import mock
from io import StringIO

class GetIdAndSeqTest(unittest.TestCase):
    def setUp(self):
        good_fasta = dedent("""
            >seq1
            AAACCCGCGCGGGTA
            >seq2
            AAAAAAAAAAAAAA

            >seq3
            CACACACACACA
            CACACACACACA
            GGGGG


        """)

        self.GOOD_DATA = good_fasta

    def test_correct_size(self):
        ids = []
        seqs = []

        data = mock.mock_open(read_data=self.GOOD_DATA)
        data.return_value.__iter__ = lambda self: self
        data.return_value.__next__ = lambda self: next(iter(self.readline, ''))
        with mock.patch('builtins.open', data) as m:
            for _id, seq in get_id_and_seq("mocked/mocked_data.fasta"):
                ids.append(_id)
                seqs.append(seq)

        # Check size of the array
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(seqs), 3)

    def test_correct_element(self):
        data = mock.mock_open(read_data=self.GOOD_DATA)
        data.return_value.__iter__ = lambda self: self
        data.return_value.__next__ = lambda self: next(iter(self.readline, ''))

        with mock.patch('builtins.open', data) as m:
            for _id, seq in get_id_and_seq("mocked/mocked_data.fasta"):
                # Check if each id has corresponding sequence
                if(_id == 'seq1'):
                    self.assertEqual(seq, 'AAACCCGCGCGGGTA')
                elif(_id == 'seq2'):
                    self.assertEqual(seq, 'AAAAAAAAAAAAAA')
                else:
                    self.assertEqual(seq, 'CACACACACACACACACACACACAGGGGG')


if __name__ == '__main__':
    unittest.main()
