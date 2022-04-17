import pandas as pd
import pytest

from scripts.qiime2_helper.triplot import (
	get_axis_breakpoints,
)



@pytest.mark.parametrize(
	("low,high,num_breaks,expected_breakpoints,expected_labels"),
	[
		(1, 7, 3, [1, 4, 7], ["1.0", "4.0", "7.0"]),
		(0.012, 0.05, 3, [0.01, 0.03, 0.05], ["0.01", "0.03", "0.05"]),
	]
)
def test_get_axis_breakpoints(low, high, num_breaks, expected_breakpoints, expected_labels):
	breakpoints, labels = get_axis_breakpoints(low, high, num_breaks)

	assert breakpoints == expected_breakpoints
	assert labels == expected_labels