"""
QIIME2 2019.10 uses pandas verion 0.18.
As a result, could not use pandas.testing module
"""
from qiime2_helper.filter_by_abundance import (
        percent_value_operation,
        calculate_percent_value,
        filter_by_abundance,
        merge_df,
        subset_df
)

import unittest
import pandas as pd
import numpy as np

class PercentValueOperationTestCase(unittest.TestCase):
    def test_non_zero_data(self):
        data = pd.Series([10, 20, 30, 40])

        expected = pd.Series([0.1, 0.2, 0.3, 0.4])
        observed = percent_value_operation(data)

        isSeriesEqual = observed.eq(expected).all()

        self.assertTrue(isSeriesEqual)

    def test_zero_data(self):
        data = pd.Series([0, 0, 0, 0])

        expected = pd.Series(np.zeros(4)) 
        observed = percent_value_operation(data)

        isSeriesEqual = observed.eq(expected).all()

        self.assertTrue(isSeriesEqual)

class SubsetDfTestCase(unittest.TestCase):
    def test_drop_no_columns(self):
        data = {'a': [1,2,3,4],
                'b': [1,2,3,4],
                'c': [1,2,3,4],
                'd': [1,2,3,4]}

        df = pd.DataFrame(data=data)
        # subset df
        cols_to_drop = []
        subset_obs, others_obs = subset_df(df, cols_to_drop)

        # expected output
        others_expected = pd.DataFrame(data)

        is_others_equal = others_expected.eq(others_obs).all().all()

        self.assertTrue(subset_obs.empty)
        self.assertTrue(is_others_equal)

    def test_drop_columns_proper(self):
        data = {'a': [1,2,3,4],
                'b': [1,2,3,4],
                'c': [1,2,3,4],
                'd': [1,2,3,4]}

        df = pd.DataFrame(data=data)
        # subset df
        cols_to_drop = ['b', 'd']
        subset_obs, others_obs = subset_df(df, cols_to_drop)

        # expected output
        expected_data_subset = {'b': [1,2,3,4],
                                'd': [1,2,3,4]}

        expected_data_others = {'a': [1,2,3,4],
                                'c': [1,2,3,4]}

        subset_expected = pd.DataFrame(data=expected_data_subset)
        others_expected = pd.DataFrame(data=expected_data_others)

        is_subset_equal = subset_expected.eq(subset_obs).all().all()
        is_others_equal = others_expected.eq(others_obs).all().all()

        self.assertTrue(is_subset_equal)
        self.assertTrue(is_others_equal)

class FilterByAbundanceTestCase(unittest.TestCase):
    def test_normal_case(self):
        # 10% cutoff threshold
        threshold = 0.1

        data = {
            'Sample1': [1,1,1,7,10],
            'Sample2': [1,1,1,10,7],
            'Sample3': [1,10,1,1,7]
        }

        idx = ['f1','f2','f3','f4','f5']

        df = pd.DataFrame(data=data, index=idx)

        filtered = filter_by_abundance(df, threshold)

        # There should be 3 rows 
        expected_nrow = 3
        observed_nrow = filtered.shape[0]

        self.assertEqual(expected_nrow, observed_nrow)

        # index name should be f2, f4, and f5
        expected_indices = ['f2', 'f4', 'f5']
        observed_indices = list(filtered.index)

        self.assertEqual(expected_indices, observed_indices)

    def test_all_filtered_case(self):
        # 90% cutoff threshold
        threshold = 0.9

        data = {
            'Sample1': [1,1,1,7,10],
            'Sample2': [1,1,1,10,7],
            'Sample3': [1,10,1,1,7]
        }

        idx = ['f1','f2','f3','f4','f5']

        df = pd.DataFrame(data=data, index=idx)

        filtered = filter_by_abundance(df, threshold)

        # There should be 3 rows 
        expected_nrow = 0
        observed_nrow = filtered.shape[0]

        self.assertEqual(expected_nrow, observed_nrow)

        # index name should be f2, f4, and f5
        expected_indices = []
        observed_indices = list(filtered.index)

        self.assertEqual(expected_indices, observed_indices)

class CalculatePercentValueTestCase(unittest.TestCase):
    def test_correct_percent_abundance(self):
        data = {
            'Sample1': [1,2,3,4],
            'Sample2': [25,25,25,25],
            'Sample3': [1,9,10,80]
        }

        df = pd.DataFrame(data=data)

        observed_abundance = calculate_percent_value(df)

        expected_data = {
            'Sample1': [0.1,0.2,0.3,0.4],
            'Sample2': [0.25,0.25,0.25,0.25],
            'Sample3': [0.01,0.09,0.10,0.80]
        }
        expected_abundance = pd.DataFrame(data=expected_data)

        isEqual = observed_abundance.eq(expected_abundance).all().all()

        self.assertTrue(isEqual)

class MergeDfTestCase(unittest.TestCase):
    def test_columns_not_in_dropped_df(self):
        # Make dropped and subset df
        data_subset = {'b': [1,2,3,4],
                        'd': [1,2,3,4]}

        data_dropped = {'a': ['a','a','a','a'],
                        'c': ['c','c','c','c']}

        subset = pd.DataFrame(data=data_subset)
        dropped = pd.DataFrame(data=data_dropped)

        cols_to_insert_at_beginning = ['e', 'f']

        with self.assertRaises(ValueError):
            merged_df = merge_df(dropped, subset, cols_to_insert_at_beginning)

    def test_merging_properly(self):
        # Make dropped and subset df
        data_subset = {'b': [1,2,3,4],
                        'd': [1,2,3,4]}

        data_dropped = {'a': ['a','a','a','a'],
                        'c': ['c','c','c','c']}

        subset = pd.DataFrame(data=data_subset)
        dropped = pd.DataFrame(data=data_dropped)

        cols_to_insert_at_beginning = ['a']

        observed_merged_df = merge_df(dropped, subset, cols_to_insert_at_beginning)

        expected_data = {
            'a': ['a','a','a','a'],
            'b': [1,2,3,4],
            'd': [1,2,3,4],
            'c': ['c','c','c','c']
        }
        expected_merged_df = pd.DataFrame(data=expected_data)

        isEqual = observed_merged_df.eq(expected_merged_df).all().all()

        self.assertTrue(isEqual)

    def test_empty_dropped_df(self):
        # Make dropped and subset df
        data_subset = {'b': [1,2,3,4],
                        'd': [1,2,3,4]}

        subset = pd.DataFrame(data=data_subset)
        dropped = pd.DataFrame()

        cols_to_insert_at_beginning = ['a']

        observed_merged_df = merge_df(dropped, subset, cols_to_insert_at_beginning)

        expected_merged_df = pd.DataFrame(data=data_subset)

        isEqual = observed_merged_df.eq(expected_merged_df).all().all()

        self.assertTrue(isEqual)

if __name__ == '__main__':
    unittest.main()
