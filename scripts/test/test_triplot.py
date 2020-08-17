import unittest
from unittest import mock

from qiime2_helper.triplot import (
	collapse_taxa
)

# Test proper exception handling
# Test empty input
# Test empty data
class TaxaCollapseTestCase(unittest.TestCase):
	def test_invalid_collapse_level(self):
		
		self.assertTrue(True)

# Test empty input
class GetVarianceExplainedTestCase(unittest.TestCase):
	def setup(self):
		pass 

if __name__ == '__main__':
	unittest.main()