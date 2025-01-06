from ukrdc_stats.calculators.krt import KRTStatsCalculator
import datetime as dt
import pandas as pd
from unittest.mock import patch, MagicMock
from ukrdc_stats.calculators.krt import KRTStatsCalculator

from unittest.mock import patch, MagicMock
import pandas as pd
import datetime as dt
import pytest

BASIC_PATIENT_COHORT = pd.DataFrame({
        'pid': [1, 1, 2, 2, 3],
        'healthcarefacilitycode': ['A', 'A', 'B', 'B', 'C'],
        'admitreasoncode' : ['A', 'A', 'B', 'B', 'C'],
        'admitreasoncodestd' : ['A', 'A', 'B', 'B', 'C'],
        'admissionsourcecode' : ['A', 'A', 'B', 'B', 'C'],  
        'admissionsourcecodestd' : ['A', 'A', 'B', 'B', 'C'],
        'qbl05' : ['A', 'A', 'B', 'B', 'C'],
        'hdp04' : ['A', 'A', 'B', 'B', 'C'],
        'dischargereasoncode' : ['A', 'A', 'B', 'B', 'C'],
        'dischargelocationcodestd' : ['A', 'A', 'B', 'B', 'C'],
        'registry_code_type' : ['A', 'A', 'B', 'B', 'C'],
        'deathtime': [dt.datetime(2020, 1, 31), dt.datetime(2020, 3, 30), dt.datetime(2020, 2, 10), dt.datetime(2020, 3, 25), dt.datetime(2020, 2, 28)],
        'fromtime': [
            dt.datetime(2020, 1, 1), dt.datetime(2020, 3, 1),
            dt.datetime(2020, 1, 10), dt.datetime(2020, 3, 5),
            dt.datetime(2020, 2, 1)
        ],
        'totime': [
            dt.datetime(2020, 1, 31), dt.datetime(2020, 3, 30),
            dt.datetime(2020, 2, 10), dt.datetime(2020, 3, 25),
            dt.datetime(2020, 2, 28)
        ],
    })

TEST_FACILITY = "RFDOG"
TEST_START = dt.datetime(2020, 1, 1)
TEST_END = dt.datetime(2020, 3, 31)

@pytest.fixture(scope='function')
def krt_calculator():
    """Fixture to initialize a KRTStatsCalculator object for testing.
    """

    session = MagicMock()
    calculator = KRTStatsCalculator(session, TEST_FACILITY, TEST_START, TEST_END)
    
    return calculator


def test_unitary_methods(krt_calculator:KRTStatsCalculator):
    """Many of the methods which transform the core patient cohort should not 
    change the extracted data. This test runs through a list of methods and
    checks them against the generic patient cohort.
    """

    method_list = [ 
        krt_calculator._add_helper_columns,
    ]

    for method in method_list:
        result = method(BASIC_PATIENT_COHORT)
        for col in BASIC_PATIENT_COHORT.columns:
            A = result[col].tolist().sort()
            B = BASIC_PATIENT_COHORT[col].tolist().sort()
            assert A == B

def test_chain_treatments():   
    
    # Patient cohort with a bunch of treament overlap scenarios
    test_patient_cohort = pd.DataFrame([
        # 1st patient has sequential treatments
        {'pid': 1, 'fromtime': dt.datetime(2020, 1, 1), 'totime': dt.datetime(2020, 1, 31), 'admitreasoncode': 'treatment_1_1'},
        {'pid': 1, 'fromtime': dt.datetime(2020, 2, 1), 'totime': dt.datetime(2020, 2, 28), 'admitreasoncode': 'treatment_1_2'},
        {'pid': 1, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 31), 'admitreasoncode': 'treatment_1_3'},
        {'pid': 1, 'fromtime': dt.datetime(2020, 4, 1), 'totime': dt.datetime(2020, 4, 30), 'admitreasoncode': 'treatment_1_4'},
        {'pid': 1, 'fromtime': dt.datetime(2020, 5, 1), 'totime': dt.datetime(2020, 5, 31), 'admitreasoncode': 'treatment_1_5'},

        # 2nd patient has overlapping treatments
        {'pid': 2, 'fromtime': dt.datetime(2020, 1, 10), 'totime': dt.datetime(2020, 2, 10), 'admitreasoncode': 'treatment_2_1'},
        {'pid': 2, 'fromtime': dt.datetime(2020, 2, 5), 'totime': dt.datetime(2020, 3, 5), 'admitreasoncode': 'treatment_2_2'},
        {'pid': 2, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 15), 'admitreasoncode': 'treatment_2_3'},
        {'pid': 2, 'fromtime': dt.datetime(2020, 3, 10), 'totime': dt.datetime(2020, 3, 25), 'admitreasoncode': 'treatment_2_4'},
        {'pid': 2, 'fromtime': dt.datetime(2020, 4, 1), 'totime': dt.datetime(2020, 4, 30), 'admitreasoncode': 'treatment_2_5'},

        # 3rd patient has short treatments during other treatments
        {'pid': 3, 'fromtime': dt.datetime(2020, 1, 15), 'totime': dt.datetime(2020, 1, 20), 'admitreasoncode': 'treatment_3_1'},
        {'pid': 3, 'fromtime': dt.datetime(2020, 1, 18), 'totime': dt.datetime(2020, 1, 19), 'admitreasoncode': 'treatment_3_2'},
        {'pid': 3, 'fromtime': dt.datetime(2020, 2, 1), 'totime': dt.datetime(2020, 2, 5), 'admitreasoncode': 'treatment_3_3'},
        {'pid': 3, 'fromtime': dt.datetime(2020, 2, 15), 'totime': dt.datetime(2020, 2, 20), 'admitreasoncode': 'treatment_3_4'},
        {'pid': 3, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 15), 'admitreasoncode': 'treatment_3_5'},

        # 4th patient with overlapping treatments and an open-ended treatment with a year-long gap
        {'pid': 4, 'fromtime': dt.datetime(2020, 2, 10), 'totime': dt.datetime(2020, 2, 20), 'admitreasoncode': 'treatment_4_1'},
        {'pid': 4, 'fromtime': dt.datetime(2020, 2, 18), 'totime': dt.datetime(2020, 3, 5), 'admitreasoncode': 'treatment_4_2'},
        {'pid': 4, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 10), 'admitreasoncode': 'treatment_4_3'},
        {'pid': 4, 'fromtime': dt.datetime(2020, 3, 10), 'totime': dt.datetime(2020, 3, 20), 'admitreasoncode': 'treatment_4_4'},
        {'pid': 4, 'fromtime': dt.datetime(2021, 3, 25), 'totime': pd.NaT, 'admitreasoncode': 'treatment_4_5'},  # Open-ended treatment
    ])



    mock_sesh = MagicMock()
    calculator = KRTStatsCalculator(mock_sesh, "", dt.datetime(1900, 1, 1), dt.datetime(1900, 1, 2))
    result = calculator._chain_treatments(test_patient_cohort)

    expected_admitreasoncode = [
        'treatment_1_1', 'treatment_1_2', 'treatment_1_3', 'treatment_1_4', 'treatment_1_5',  # Patient 1
        'treatment_2_1', 'treatment_2_2', 'treatment_2_3', 'treatment_2_4', 'treatment_2_5',  # Patient 2
        'treatment_3_1', 'treatment_3_2', 'treatment_3_3', 'treatment_3_4', 'treatment_3_5',  # Patient 3
        'treatment_4_1', 'treatment_4_2', 'treatment_4_3', 'treatment_4_4', 'treatment_4_5',  # Patient 4
    ]
    actual_admitreasoncode = result.sort_values(['pid', 'fromtime']).admitreasoncode.tolist()

    
    assert expected_admitreasoncode == actual_admitreasoncode



@patch('ukrdc_stats.calculators.krt.KRTStatsCalculator._extract_base_patient_cohort')
def test_add_helper_columns(mock_extract_base_patient_cohort):
    # Mock return value for _extract_base_patient_cohort
    mock_base_cohort = pd.DataFrame({
        'pid': [1, 1, 2, 2, 3],
        'fromtime': [
            dt.datetime(2020, 1, 1), dt.datetime(2020, 3, 1),
            dt.datetime(2020, 1, 10), dt.datetime(2020, 3, 5),
            dt.datetime(2020, 2, 1)
        ],
        'totime': [
            dt.datetime(2020, 1, 31), dt.datetime(2020, 3, 30),
            dt.datetime(2020, 2, 10), dt.datetime(2020, 3, 25),
            dt.datetime(2020, 2, 28)
        ],
        'healthcarefacilitycode': ['A', 'A', 'B', 'B', 'C']
    })
    mock_extract_base_patient_cohort.return_value = mock_base_cohort

    # Initialize the calculator
    session = MagicMock()  # Mock session
    start = dt.datetime(2020, 1, 1)
    end = dt.datetime(2020, 3, 31)
    facility = "RFDOG"
    calculator = KRTStatsCalculator(session, facility, start, end)

    # Call the method under test
    result = calculator._add_helper_columns(mock_base_cohort)

    # Validate the helper columns
    assert 'most_recent' in result.columns
    assert 'first_treatment' in result.columns

    # Check specific values for correctness
    # Validate `most_recent` logic
    assert result.loc[(result['pid'] == 1) & (result['fromtime'] == dt.datetime(2020, 3, 1)), 'most_recent'].iloc[0] == True
    assert result.loc[(result['pid'] == 1) & (result['fromtime'] == dt.datetime(2020, 1, 1)), 'most_recent'].iloc[0] == False

    # Validate `first_treatment` logic
    assert result.loc[(result['pid'] == 1) & (result['fromtime'] == dt.datetime(2020, 1, 1)), 'first_treatment'].iloc[0] == True
    assert result.loc[(result['pid'] == 1) & (result['fromtime'] == dt.datetime(2020, 3, 1)), 'first_treatment'].iloc[0] == False

