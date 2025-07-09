
import pytest
import pandas as pd
from ukrdc_stats.calculators.demographics import _calculate_base_patient_histogram


import pytest
import pandas as pd
import polars as pl
import datetime as dt

from ukrdc_stats.calculators.demographics import (
    DemographicStatsCalculator,
    _calculate_base_patient_histogram,
)
from unittest.mock import MagicMock, patch



@pytest.fixture
def sample_cohort():
    """Fixture to provide sample cohort data."""
    return pl.DataFrame({
        "ukrdcid": [1, 2, 3, 4, 5, 6],
        "group_col": ["A", "B", "A", "C", "A", "C"],
        "gender": ["1", "2", "1", "X", "1", "9"],
        "ethnic_group_code": ["A", "B", "A", "C", "A", "C"],
        "birth_time": [
            dt.datetime(2000, 1, 1),
            dt.datetime(1990, 5, 15),
            dt.datetime(1985, 3, 10),
            dt.datetime(2001, 6, 20),
            dt.datetime(2000, 1, 1),
            dt.datetime(1995, 9, 25),
        ],
        "death_time": [None, None, None, None, None, None],
    })


@pytest.fixture
def code_map():
    """Fixture to provide a code map."""
    return {"A": "Alice", "B": "Bob", "C": "Charlie"}


@pytest.fixture
def empty_cohort():
    """Fixture to provide an empty cohort dataframe."""
    return pl.DataFrame()


@pytest.fixture
def demographics_calculator(sample_cohort):
    """Fixture to mock the demographics calculator."""
    calculator = DemographicStatsCalculator(session=MagicMock(), facility="RFDOG", end_date=dt.datetime(2025, 1, 1))
    
    # Overwrite data with sample cohort
    calculator._patient_cohort = sample_cohort

    return calculator


def test_calculate_gender(demographics_calculator):

    gender_hist = demographics_calculator._calculate_gender()
    assert gender_hist.data.x == ['Female', 'Indeterminate', 'Male', 'Unknown']
    assert gender_hist.data.y == [1,1,3,1]


def test_calculate_ethnicity(demographics_calculator):
    with patch("ukrdc_stats.calculators.demographics.map_codes", return_value={"A": "GroupA", "B": "GroupB", "C": "GroupC"}):
        ethnicity = demographics_calculator._calculate_ethnic_group_code()

    assert ethnicity.data.x == ['GroupA', 'GroupB', 'GroupC']
    assert ethnicity.data.y == [3, 1, 2]

def test_calculate_age(demographics_calculator):
    """Test calculation of age demographics."""
    age_hist = demographics_calculator._calculate_age()

    assert age_hist.data.x == ['23', '25', '29', '34', '39']
    assert age_hist.data.y == [1, 2, 1, 1, 1]


def test_histogram_without_code_map(sample_cohort):
    """Test the histogram calculation without a code map."""
    expected_result = pl.DataFrame({
        "group_col": ["A", "B", "C"],
        "Count": [3, 1, 2],
    })

    result = _calculate_base_patient_histogram(sample_cohort, "group_col")

    assert result.sort("group_col").equals(
        expected_result.sort("group_col")
    )

def test_histogram_with_code_map(sample_cohort, code_map):
    expected_result = pl.DataFrame({
        "group_col_mapped": ["Alice", "Bob", "Charlie"],
        "Count": [3, 1, 2],
    })
    result = _calculate_base_patient_histogram(sample_cohort,"group_col", code_map)
    
    assert result.sort("group_col_mapped").equals(
        expected_result.sort("group_col_mapped")
    )
