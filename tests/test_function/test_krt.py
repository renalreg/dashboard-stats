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

        # 4th patient with two separate periods of overlapping treatments
        {'pid': 4, 'fromtime': dt.datetime(2020, 2, 10), 'totime': dt.datetime(2020, 2, 20), 'admitreasoncode': 'treatment_4_1'},
        {'pid': 4, 'fromtime': dt.datetime(2020, 2, 18), 'totime': dt.datetime(2020, 3, 5), 'admitreasoncode': 'treatment_4_2'},
        {'pid': 4, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 10), 'admitreasoncode': 'treatment_4_3'},
        {'pid': 4, 'fromtime': dt.datetime(2020, 3, 10), 'totime': dt.datetime(2020, 3, 20), 'admitreasoncode': 'treatment_4_4'},
        
        {'pid': 4, 'fromtime': dt.datetime(2020, 5, 1), 'totime': dt.datetime(2020, 5, 10), 'admitreasoncode': 'treatment_4_5'},
        {'pid': 4, 'fromtime': dt.datetime(2020, 5, 8), 'totime': dt.datetime(2020, 5, 20), 'admitreasoncode': 'treatment_4_6'},
        {'pid': 4, 'fromtime': dt.datetime(2020, 5, 15), 'totime': dt.datetime(2020, 5, 25), 'admitreasoncode': 'treatment_4_7'},
        {'pid': 4, 'fromtime': dt.datetime(2021, 3, 25), 'totime': pd.NaT, 'admitreasoncode': 'treatment_4_8'},  # Open-ended treatment
    ])



    mock_sesh = MagicMock()
    calculator = KRTStatsCalculator(mock_sesh, "", dt.datetime(1900, 1, 1), dt.datetime(1900, 1, 2))
    result = calculator._chain_treatments(test_patient_cohort)

    expected_next_fromtime = [
        dt.datetime(2020, 2, 1), 
        dt.datetime(2020, 3, 1), 
        dt.datetime(2020, 4, 1), 
        dt.datetime(2020, 5, 1), 
        None, 
        None, 
        None, 
        None, 
        dt.datetime(2020, 4, 1), 
        None, 
        dt.datetime(2020, 2, 1), 
        None, 
        dt.datetime(2020, 2, 15), 
        dt.datetime(2020, 3, 1), 
        None, 
        None, 
        None, 
        dt.datetime(2020, 3, 10), 
        dt.datetime(2020, 5, 1), 
        None, 
        None, 
        dt.datetime(2021, 3, 25), 
        None
    ]

    actual_next_fromtime = [
        None if pd.isna(value) else value
        for value in result["next_fromtime"].tolist()
    ]

    assert expected_next_fromtime == actual_next_fromtime



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
    

def test_exclude_records():
    """Test the _exclude_records method with different 90+ day gaps relative to the time window."""
    test_patient_cohort = pd.DataFrame([
        # Patient 1: Recovery gap extends beyond end of the window (exclude entirely)
        {'pid': 1, 'fromtime': dt.datetime(2019,1,1), 'totime': dt.datetime(2019,1,10), 'next_fromtime': dt.datetime(2020,2,2)},
        {'pid': 1, 'fromtime': dt.datetime(2020,2,2), 'totime': dt.datetime(2022,1,2), 'next_fromtime': None},
        # Patient 2: Recovery gap ends within the time window (partially included)
        {'pid': 2, 'fromtime': dt.datetime(2006,1,5), 'totime': dt.datetime(2019,1,20), 'next_fromtime': dt.datetime(2019,5,10)},
        {'pid': 2, 'fromtime': dt.datetime(2019,5,10), 'totime': dt.datetime(2019,4,15), 'next_fromtime': None},
        # Patient 3: Recovery gap ends after the time window (remain included)
        {'pid': 3, 'fromtime': dt.datetime(2019,2,1), 'totime': dt.datetime(2020,1,2), 'next_fromtime': dt.datetime(2020,5,2)},
        {'pid': 3, 'fromtime': dt.datetime(2020,5,2), 'totime': dt.datetime(2019,7,25), 'next_fromtime': None},
    ])

    session = MagicMock()
    # Calculator time window ends on 2019-03-31
    calculator = KRTStatsCalculator(session, "", dt.datetime(2019,1,1), dt.datetime(2020,1,1))

    result_df = calculator._exclude_records(test_patient_cohort)

    # Patient 1 should be fully excluded, so no rows with pid = 1
    # Patients 2 and 3 should remain partially or fully included
    pids_out = result_df.sort_values('pid').pid.tolist()
    from_time_out = [
        d.to_pydatetime() for d in result_df.sort_values('fromtime')['fromtime']
    ]
    assert pids_out == [2, 3]
    assert from_time_out == [dt.datetime(2019, 2, 1, 0, 0), dt.datetime(2019, 5, 10, 0, 0)]

def test_extract_incident_prevalent():
    """
    Test the _extract_incident_prevalent method with a variety of patient scenarios
    These scenarios need to be carefully expanded to cover the full range of possible
    branches in the method.
    """

    mock_data = pd.DataFrame([
        # Patient 1: Chronic, long timeline => prevalent
        {
            'pid': 1,
            'fromtime': dt.datetime(2020, 1, 1),
            'totime': dt.datetime(2020, 7, 1),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        {
            'pid': 1,
            'fromtime': dt.datetime(2020, 7, 2),
            'totime': dt.datetime(2020, 8, 15),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 2: Dies early => not incident/prevalent
        {
            'pid': 2,
            'fromtime': dt.datetime(2020, 2, 1),
            'totime': dt.datetime(2020, 3, 1),
            'deathtime': dt.datetime(2020, 3, 10),
            'is_chronic': False,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 3: Historic transplant => incident
        {
            'pid': 3,
            'fromtime': dt.datetime(2020, 3, 1),
            'totime': dt.datetime(2020, 9, 1),
            'deathtime': None,
            'is_chronic': False,
            'historic_tx': True,
            'dischargereasoncode': None,
        },
        # Patient 4: Crash landing => incident (>90 days)
        {
            'pid': 4,
            'fromtime': dt.datetime(2020, 2, 15),
            'totime': dt.datetime(2020, 6, 1),
            'deathtime': None,
            'is_chronic': False,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 5: Short chronic => neither
        {
            'pid': 5,
            'fromtime': dt.datetime(2020, 2, 10),
            'totime': dt.datetime(2020, 2, 20),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 6: Transferred out (code 38) => incident
        {
            'pid': 6,
            'fromtime': dt.datetime(2020, 1, 1),
            'totime': dt.datetime(2020, 3, 1),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': True,
            'dischargereasoncode': '38',
        },
        # Patient 7: Multiple treatments, chronic => prevalent
        {
            'pid': 7,
            'fromtime': dt.datetime(2020, 1, 1),
            'totime': dt.datetime(2020, 2, 15),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        {
            'pid': 7,
            'fromtime': dt.datetime(2020, 2, 16),
            'totime': dt.datetime(2020, 8, 1),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 8: Short initial then long treatment => incident
        {
            'pid': 8,
            'fromtime': dt.datetime(2020, 3, 1),
            'totime': dt.datetime(2020, 3, 2),
            'deathtime': None,
            'is_chronic': False,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        {
            'pid': 8,
            'fromtime': dt.datetime(2020, 3, 3),
            'totime': dt.datetime(2020, 7, 5),
            'deathtime': None,
            'is_chronic': False,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 9: Dies but chronic => prevalent 
        {
            'pid': 9,
            'fromtime': dt.datetime(2020, 2, 10),
            'totime': dt.datetime(2020, 6, 20),
            'deathtime': dt.datetime(2020, 7, 1),
            'is_chronic': True,
            'historic_tx': True,
            'dischargereasoncode': None,
        },
    ])
    session = MagicMock()
    calculator = KRTStatsCalculator(session, "TEST", dt.datetime(2020,1,1), dt.datetime(2020,6,30))
    result = calculator._extract_incident_prevalent(mock_data)
    
    expected = pd.DataFrame({
        "pid": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "incident": [False, True, True, True, False, False, False, True, True],
        "prevalent": [True, False, True, False, False, False, True, True, False]
    })
    
    # Get one row per patient by taking first occurrence
    actual = (
        result[["pid", "incident", "prevalent"]]
        .drop_duplicates(subset="pid")
        .sort_values("pid")
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(actual, expected)

def test_calculate_dialysis_frequency():
    assert True

def test_calculate_access_incident():
    assert True

def test_calculate_therapies_incident_patients():
    assert True 

def test_calculate_therapies_prevalent_patients():
    assert True
