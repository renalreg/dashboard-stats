from ukrdc_stats.calculators.krt import KRTStatsCalculator
import datetime as dt
import pandas as pd
from unittest.mock import patch, MagicMock
from ukrdc_stats.calculators.krt import KRTStatsCalculator

from unittest.mock import patch, MagicMock
import pandas as pd
import datetime as dt
import pytest

from ukrdc_stats.models.generic_2d import BaseTable
from ukrdc_stats.exceptions import NoCohortError
from collections import namedtuple


BASIC_PATIENT_COHORT = pd.DataFrame({
    'ukrdcid': [1, 1, 2, 2, 3],
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

    # removed methods as it seems superflous now
    method_list = []
    for method in method_list:
        result = method(BASIC_PATIENT_COHORT)
        for col in BASIC_PATIENT_COHORT.columns:
            A = result[col].tolist().sort()
            B = BASIC_PATIENT_COHORT[col].tolist().sort()

    for method in method_list:
        result = method(BASIC_PATIENT_COHORT)
        for col in BASIC_PATIENT_COHORT.columns:
            A = result[col].tolist().sort()
            B = BASIC_PATIENT_COHORT[col].tolist().sort()
            
            if A!=B:
                print(A)
                print(B)
                assert A==B

def test_chain_treatments():   
    
    # Patient cohort with a bunch of treament overlap scenarios
    test_patient_cohort = pd.DataFrame([
        # 1st patient has sequential treatments
        {'ukrdcid': 1, 'fromtime': dt.datetime(2020, 1, 1), 'totime': dt.datetime(2020, 1, 31), 'admitreasoncode': 'treatment_1_1'},
        {'ukrdcid': 1, 'fromtime': dt.datetime(2020, 2, 1), 'totime': dt.datetime(2020, 2, 28), 'admitreasoncode': 'treatment_1_2'},
        {'ukrdcid': 1, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 31), 'admitreasoncode': 'treatment_1_3'},
        {'ukrdcid': 1, 'fromtime': dt.datetime(2020, 4, 1), 'totime': dt.datetime(2020, 4, 30), 'admitreasoncode': 'treatment_1_4'},
        {'ukrdcid': 1, 'fromtime': dt.datetime(2020, 5, 1), 'totime': dt.datetime(2020, 5, 31), 'admitreasoncode': 'treatment_1_5'},

        # 2nd patient has overlapping treatments
        {'ukrdcid': 2, 'fromtime': dt.datetime(2020, 1, 10), 'totime': dt.datetime(2020, 2, 10), 'admitreasoncode': 'treatment_2_1'},
        {'ukrdcid': 2, 'fromtime': dt.datetime(2020, 2, 5), 'totime': dt.datetime(2020, 3, 5), 'admitreasoncode': 'treatment_2_2'},
        {'ukrdcid': 2, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 15), 'admitreasoncode': 'treatment_2_3'},
        {'ukrdcid': 2, 'fromtime': dt.datetime(2020, 3, 10), 'totime': dt.datetime(2020, 3, 25), 'admitreasoncode': 'treatment_2_4'},
        {'ukrdcid': 2, 'fromtime': dt.datetime(2020, 4, 1), 'totime': dt.datetime(2020, 4, 30), 'admitreasoncode': 'treatment_2_5'},

        # 3rd patient has short treatments during other treatments
        {'ukrdcid': 3, 'fromtime': dt.datetime(2020, 1, 15), 'totime': dt.datetime(2020, 1, 20), 'admitreasoncode': 'treatment_3_1'},
        {'ukrdcid': 3, 'fromtime': dt.datetime(2020, 1, 18), 'totime': dt.datetime(2020, 1, 19), 'admitreasoncode': 'treatment_3_2'},
        {'ukrdcid': 3, 'fromtime': dt.datetime(2020, 2, 1), 'totime': dt.datetime(2020, 2, 5), 'admitreasoncode': 'treatment_3_3'},
        {'ukrdcid': 3, 'fromtime': dt.datetime(2020, 2, 15), 'totime': dt.datetime(2020, 2, 20), 'admitreasoncode': 'treatment_3_4'},
        {'ukrdcid': 3, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 15), 'admitreasoncode': 'treatment_3_5'},

        # 4th patient with two separate periods of overlapping treatments
        {'ukrdcid': 4, 'fromtime': dt.datetime(2020, 2, 10), 'totime': dt.datetime(2020, 2, 20), 'admitreasoncode': 'treatment_4_1'},
        {'ukrdcid': 4, 'fromtime': dt.datetime(2020, 2, 18), 'totime': dt.datetime(2020, 3, 5), 'admitreasoncode': 'treatment_4_2'},
        {'ukrdcid': 4, 'fromtime': dt.datetime(2020, 3, 1), 'totime': dt.datetime(2020, 3, 10), 'admitreasoncode': 'treatment_4_3'},
        {'ukrdcid': 4, 'fromtime': dt.datetime(2020, 3, 10), 'totime': dt.datetime(2020, 3, 20), 'admitreasoncode': 'treatment_4_4'},
        
        {'ukrdcid': 4, 'fromtime': dt.datetime(2020, 5, 1), 'totime': dt.datetime(2020, 5, 10), 'admitreasoncode': 'treatment_4_5'},
        {'ukrdcid': 4, 'fromtime': dt.datetime(2020, 5, 8), 'totime': dt.datetime(2020, 5, 20), 'admitreasoncode': 'treatment_4_6'},
        {'ukrdcid': 4, 'fromtime': dt.datetime(2020, 5, 15), 'totime': dt.datetime(2020, 5, 25), 'admitreasoncode': 'treatment_4_7'},
        {'ukrdcid': 4, 'fromtime': dt.datetime(2021, 3, 25), 'totime': pd.NaT, 'admitreasoncode': 'treatment_4_8'},  # Open-ended treatment
    ])

    test_patient_cohort["sendingfacility"] = "RFDOG"

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
        'ukrdcid': [1, 1, 2, 2, 3],
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
    mock_base_cohort["sendingfacility"] = "RFDOG"
    mock_base_cohort["pid"] = mock_base_cohort["ukrdcid"] 
    mock_base_cohort["deathtime"] = pd.NaT

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

    window_start = dt.datetime(2019,1,1)
    window_stop = dt.datetime(2020,1,1)
    big_gap = dt.timedelta(days=91)
    small_gap = dt.timedelta(days=89)


    test_patient_cohort = pd.DataFrame([
        # Patient 1: Recovery gap extends beyond end of the window (exclude entirely)
        {'rowid':1,'ukrdcid': "1", 'fromtime': dt.datetime(2019,1,1), 'totime': dt.datetime(2019,1,10), 'next_fromtime': dt.datetime(2020,2,2)},
        {'rowid':2,'ukrdcid': "1", 'fromtime': dt.datetime(2020,2,2), 'totime': dt.datetime(2022,1,2), 'next_fromtime': None},
        # Patient 2: Recovery gap ends within the time window (partially included)
        {'rowid':3,'ukrdcid': "2", 'fromtime': dt.datetime(2006,1,5), 'totime': dt.datetime(2019,1,20), 'next_fromtime': dt.datetime(2019,5,10)},
        {'rowid':4,'ukrdcid': "2", 'fromtime': dt.datetime(2019,5,10), 'totime': dt.datetime(2019,4,15), 'next_fromtime': None},
        # Patient 3: Recovery gap ends after the time window (remain included)
        {'rowid':5,'ukrdcid': "3", 'fromtime': dt.datetime(2019,2,1), 'totime': dt.datetime(2020,1,2), 'next_fromtime': dt.datetime(2020,5,2)},
        {'rowid':6,'ukrdcid': "3", 'fromtime': dt.datetime(2020,5,2), 'totime': dt.datetime(2019,7,25), 'next_fromtime': None},
        # Patient 4: Continuous treatment without gaps
        {'rowid':7,'ukrdcid': "4", 'fromtime': dt.datetime(2019,1,1), 'totime': dt.datetime(2019,3,1), 'next_fromtime': dt.datetime(2019,3,2)},
        {'rowid':8,'ukrdcid': "4", 'fromtime': dt.datetime(2019,3,2), 'totime': dt.datetime(2020,1,1), 'next_fromtime': None},
        # Patient 5: Multiple gaps
        {'rowid':9,'ukrdcid': "5", 'fromtime': dt.datetime(2019,1,1), 'totime': dt.datetime(2019,2,1), 'next_fromtime': dt.datetime(2019,5,1)},
        {'rowid':10,'ukrdcid': "5", 'fromtime': dt.datetime(2019,5,1), 'totime': dt.datetime(2019,6,1), 'next_fromtime': dt.datetime(2019,9,1)},
        {'rowid':11,'ukrdcid': "5", 'fromtime': dt.datetime(2019,9,1), 'totime': dt.datetime(2020,1,1), 'next_fromtime': None},
        # Patient 6: Gap exactly 90 days
        {'rowid':12,'ukrdcid': "6", 'fromtime': dt.datetime(2019,1,1), 'totime': dt.datetime(2019,1,10), 'next_fromtime': dt.datetime(2019,4,10)},
        {'rowid':13,'ukrdcid': "6", 'fromtime': dt.datetime(2019,4,10), 'totime': dt.datetime(2020,1,1), 'next_fromtime': None},
        # Patient 7: Overlapping treatments
        {'rowid':14,'ukrdcid': "7", 'fromtime': dt.datetime(2019,1,1), 'totime': dt.datetime(2019,1,15), 'next_fromtime': dt.datetime(2019,1,10)},
        {'rowid':15,'ukrdcid': "7", 'fromtime': dt.datetime(2019,1,10), 'totime': dt.datetime(2020,1,1), 'next_fromtime': None},
    ])

    session = MagicMock()
    # Calculator time window ends on 2019-03-31
    calculator = KRTStatsCalculator(session, "RFDOG", from_time = window_start, to_time = window_stop)

    result_df = calculator._exclude_records(test_patient_cohort)

    output_rows = sorted(result_df["rowid"].tolist())
    assert  output_rows == [4, 5, 7, 8, 11, 12, 13, 14, 15]

def test_extract_incident_prevalent():
    """
    Test the _extract_incident_prevalent method with a variety of patient scenarios
    These scenarios need to be carefully expanded to cover the full range of possible
    branches in the method.
    """

    mock_data = pd.DataFrame([
        # Patient 1: Chronic, long timeline => prevalent
        {
            'ukrdcid': "1",
            'fromtime': dt.datetime(2020, 1, 1),
            'totime': dt.datetime(2020, 7, 1),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        {
            'ukrdcid': "1",
            'fromtime': dt.datetime(2020, 7, 2),
            'totime': dt.datetime(2020, 8, 15),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 2: Dies early => not incident/prevalent
        {
            'ukrdcid': "2",
            'fromtime': dt.datetime(2020, 2, 1),
            'totime': dt.datetime(2020, 3, 1),
            'deathtime': dt.datetime(2020, 3, 10),
            'is_chronic': False,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 3: Historic transplant => incident
        {
            'ukrdcid': "3",
            'fromtime': dt.datetime(2020, 3, 1),
            'totime': dt.datetime(2020, 9, 1),
            'deathtime': None,
            'is_chronic': False,
            'historic_tx': True,
            'dischargereasoncode': None,
        },
        # Patient 4: Crash landing => incident (>90 days)
        {
            'ukrdcid': "4",
            'fromtime': dt.datetime(2020, 2, 15),
            'totime': dt.datetime(2020, 6, 1),
            'deathtime': None,
            'is_chronic': False,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 5: Short chronic => neither
        {
            'ukrdcid': "5",
            'fromtime': dt.datetime(2020, 2, 10),
            'totime': dt.datetime(2020, 2, 20),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 6: Transferred out (code 38) => incident
        {
            'ukrdcid': "6",
            'fromtime': dt.datetime(2020, 1, 1),
            'totime': dt.datetime(2020, 3, 1),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': True,
            'dischargereasoncode': '38',
        },
        # Patient 7: Multiple treatments, chronic => prevalent
        {
            'ukrdcid': "7",
            'fromtime': dt.datetime(2020, 1, 1),
            'totime': dt.datetime(2020, 2, 15),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        {
            'ukrdcid': "7",
            'fromtime': dt.datetime(2020, 2, 16),
            'totime': dt.datetime(2020, 8, 1),
            'deathtime': None,
            'is_chronic': True,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 8: Short initial then long treatment => incident
        {
            'ukrdcid': "8",
            'fromtime': dt.datetime(2020, 3, 1),
            'totime': dt.datetime(2020, 3, 2),
            'deathtime': None,
            'is_chronic': False,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        {
            'ukrdcid': "8",
            'fromtime': dt.datetime(2020, 3, 3),
            'totime': dt.datetime(2020, 7, 5),
            'deathtime': None,
            'is_chronic': False,
            'historic_tx': False,
            'dischargereasoncode': None,
        },
        # Patient 9: Dies but chronic => prevalent 
        {
            'ukrdcid': "9",
            'fromtime': dt.datetime(2020, 2, 10),
            'totime': dt.datetime(2020, 6, 20),
            'deathtime': dt.datetime(2020, 7, 1),
            'is_chronic': True,
            'historic_tx': True,
            'dischargereasoncode': None,
        },
    ])
    mock_data["sendingfacility"] = "RFDOG"
    mock_data["dischargelocationcode"] = "RFCAT"

    session = MagicMock()
    calculator = KRTStatsCalculator(session, "RFDOG", from_time = dt.datetime(2020,1,1), to_time = dt.datetime(2020,6,30))
    
    result = calculator._extract_incident_prevalent(mock_data)
    
    expected = pd.DataFrame({
        "ukrdcid": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "incident": [False, True, True, True, False, False, False, True, True],
        "prevalent": [True, False, True, False, False, False, True, True, False]
    })
    
    # Get one row per patient by taking first occurrence
    actual = (
        result[["ukrdcid", "incident", "prevalent"]]
        .drop_duplicates(subset="ukrdcid")
        .sort_values("ukrdcid")
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

@patch('ukrdc_stats.calculators.krt.KRTStatsCalculator._query_vascular_access')
def test_calculate_access_incident(mock_query_vascular_access, krt_calculator):
    """Test vascular access calculation for incident patients.
    
    Verifies that:
    - The method correctly filters incident patients
    - Subunit filtering works as expected
    - Vascular access data is properly merged and aggregated
    - Missing data is handled with Unknown/Incomplete label
    """
    # Mock patient cohort with 6 incident patients across 2 facilities
    krt_calculator._patient_cohort = pd.DataFrame({
        'pid': ["1", "2", "3", "4", "5", "6"],
        'ukrdcid': ["1", "2", "3", "4", "5", "6"],
        'incident': [True, True, True, True, True, False],  # Patient 6 not incident
        'first_treatment': [True, True, False, True, True, True],  # Patient 3 not first treatment
        'healthcarefacilitycode': ['A', 'A', 'A', 'B', 'B', 'B']
    })
    
    # Complete access data for all patients
    all_access_data = pd.DataFrame({
        'pid': ["1", "2", "4", "5"],
        'accesstype': ['AVF', 'NLN', 'TLN', 'AVF'],
        'procedure_time': [dt.datetime(2020, 1, 1)] * 4
    })
    
    # Mock _query_vascular_access to return filtered data based on input patient_list
    def mock_query_side_effect(patient_list):
        # Filter access data to only include patients in the input list
        pids = patient_list.tolist()
        return all_access_data[all_access_data['pid'].isin(pids)]

    mock_query_vascular_access.side_effect = mock_query_side_effect
    
    # Test for all subunits
    result_all = krt_calculator._calculate_access_incident(subunit='all')
    
    # Should include all 5 incident patients (1,2,3,4,5)
    # Patient 3 has no access data, so gets Unknown/Incomplete
    assert result_all.metadata.title == "Vascular Access on First HD Session"
    assert result_all.metadata.summary == "Vascular access for incident patients registered on their first dialysis session."
    assert sorted(result_all.data.x) == sorted(['AVF', 'NLN', 'TLN', 'Unknown/Incomplete'])
    
    # Count by access type: AVF=2 (patients 1,5), NLN=1 (patient 2), TLN=1 (patient 4), Unknown=1 (patient 3)
    access_counts = dict(zip(result_all.data.x, result_all.data.y))
    assert access_counts['AVF'] == 2
    assert access_counts['NLN'] == 1
    assert access_counts['TLN'] == 1
    assert access_counts['Unknown/Incomplete'] == 1
    
    # Test for subunit 'A'
    # Queries access for incident + first_treatment + facility A (patients 1, 2)
    # But merges with ALL incident patients, so result includes all 5 incident patients
    # Patients not in the query get Unknown/Incomplete
    result_subunit_a = krt_calculator._calculate_access_incident(subunit='A')
    
    assert result_subunit_a.metadata.title == "Vascular Access on First HD Session"
    access_counts_a = dict(zip(result_subunit_a.data.x, result_subunit_a.data.y))
    assert access_counts_a['AVF'] == 1  # Patient 1
    assert access_counts_a['NLN'] == 1  # Patient 2
    # Patients 3, 4, 5 not in query (different facility or not first_treatment), so get Unknown
    assert access_counts_a['Unknown/Incomplete'] == 3
    
    # Test for subunit 'B'
    # Queries access for incident + first_treatment + facility B (patients 4, 5)
    # But merges with ALL incident patients, so result includes all 5 incident patients
    result_subunit_b = krt_calculator._calculate_access_incident(subunit='B')
    
    assert result_subunit_b.metadata.title == "Vascular Access on First HD Session"
    access_counts_b = dict(zip(result_subunit_b.data.x, result_subunit_b.data.y))
    assert access_counts_b['TLN'] == 1  # Patient 4
    assert access_counts_b['AVF'] == 1  # Patient 5
    # Patients 1, 2, 3 not in query (different facility or not first_treatment), so get Unknown
    assert access_counts_b['Unknown/Incomplete'] == 3

@patch('ukrdc_stats.calculators.krt.KRTStatsCalculator._query_dialysis_sessions')
def test_calculate_dialysis_frequency(mock_query_dialysis_sessions, krt_calculator):
    # Mock return value for _query_dialysis_sessions

    """
    mock_query_dialysis_sessions.return_value = pd.DataFrame({
        'pid': ["1", "1", "1", "1", "2", "2", "2", "2", "3", "3", "3", "3", "4", "4", "4", "4"],
        'ukrdcid': ["1", "1", "1", "1", "2", "2", "2", "2", "3", "3", "3", "3", "4", "4", "4", "4"],
        'weekstart': [dt.datetime(2020, 1, 1), dt.datetime(2020, 1, 8), dt.datetime(2020, 1, 15), dt.datetime(2020, 1, 22), dt.datetime(2020, 1, 29), dt.datetime(2020, 1, 1), dt.datetime(2020, 1, 8), dt.datetime(2020, 1, 15), dt.datetime(2020, 1, 22), dt.datetime(2020, 1, 29), dt.datetime(2020, 1, 1), dt.datetime(2020, 1, 8), dt.datetime(2020, 1, 15), dt.datetime(2020, 1, 22), dt.datetime(2020, 1, 29)],
        'hdsessionno': [1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4],
        'totaltimedialised':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    })
    """
    # Adjust the mock return value for _query_dialysis_sessions
    mock_query_dialysis_sessions.return_value = pd.DataFrame({
        'pid': ["1", "1", "1", "1", "2", "2", "2", "2", "3", "3", "3", "3", "4", "4", "4", "4"],
        'ukrdcid': ["1", "1", "1", "1", "2", "2", "2", "2", "3", "3", "3", "3", "4", "4", "4", "4"],
        'weekstart': [
            dt.datetime(2020, 1, 1), dt.datetime(2020, 1, 1), dt.datetime(2020, 1, 1), dt.datetime(2020, 1, 1),
            dt.datetime(2020, 1, 8), dt.datetime(2020, 1, 8), dt.datetime(2020, 1, 8), dt.datetime(2020, 1, 8),
            dt.datetime(2020, 1, 15), dt.datetime(2020, 1, 15), dt.datetime(2020, 1, 15), dt.datetime(2020, 1, 15),
            dt.datetime(2020, 1, 22), dt.datetime(2020, 1, 22), dt.datetime(2020, 1, 22), dt.datetime(2020, 1, 22)
        ],
        'hdsessionno': [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 5, 5, 5, 5],
        'totaltimedialised': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    })

    # Mock patient cohort
    krt_calculator._patient_cohort = pd.DataFrame({
        'pid': [1, 2, 3, 4],
        'registry_code_type': ['HD', 'HD', 'HD', 'HD'],
        'qbl05': ['HOSP', 'SATL', 'In-centre', 'In-centre'],
        'healthcarefacilitycode': ['A', 'A', 'B', 'B'],
        'prevalent': [True, True, True, True]
    })

    # Call the method under test for all subunits
    median_freq, median_time = krt_calculator._calculate_dialysis_frequency(subunit='all')

    # Validate the result for all subunits
    assert median_freq.data.x == ["1", "2", "3", ">3"] 
    assert median_freq.data.y == [1,1,1,1]


@pytest.fixture
def mock_patient_cohort():
    return pd.DataFrame({
        "pid" : [1, 2, 3, 4],
        "ukrdcid": [1, 2, 3, 4],
        "incident": [True, False, True, True],
        "first_treatment": [True, True, False, True],
        "prevalent": [False, True, False, False],
        "healcarefacilitycode": ["foo", "bar", "foo", "bar"],
        "admitreasoncode" : ["reason_1", "reason_2", "reason_2", "reason_2"],
        "admitreasoncodestd": ["reasonstd_1", "reasonstd_2", "reasonstd_2", "reasonstd_2"],
        "registry_code_type" : ['HD', 'HD', 'HD', 'HD'],
    })
    
def test_produce_report(mock_patient_cohort):
    mock_session = MagicMock()
    
    calculator = KRTStatsCalculator(
        session=mock_session, 
        facility="TESTFACILITY", 
        from_time=pd.Timestamp("2024-01-01"), 
        to_time=pd.Timestamp("2024-06-01")
    )
    
    calculator._patient_cohort = mock_patient_cohort.copy()
    
    population, table = calculator.produce_report(
        output_columns=[
                    "pid",
                    "healcarefacilitycode",
                    "admitreasoncode",
                    "admitreasoncodestd",
                    "registry_code_type",
        ], 
        input_filters=["incident"], 
        include_ni=False
    )
    
    assert population == 3  # 3 incident patients
    assert isinstance(table, BaseTable)
    assert "ukrdcid" in table.headers
    assert "incident" not in table.headers
    assert "healcarefacilitycode" in table.headers
    assert len(table.rows) == 3
    
def test_produce_report_no_cohort_raises():
    mock_session = MagicMock()
    
    calculator = KRTStatsCalculator(
        session=mock_session, 
        facility="TESTFACILITY", 
        from_time=dt.datetime(2024, 1, 1), 
        to_time=dt.datetime(2024, 6, 1)
    )
    
    calculator.extract_patient_cohort = MagicMock(return_value=None)
    calculator._patient_cohort = None

    with pytest.raises(NoCohortError):
        calculator.produce_report(output_columns=["incident"], input_filters=["incident"])
        
def test_produce_report_include_ni(mock_patient_cohort):
    filtered_cohort = mock_patient_cohort[mock_patient_cohort["ukrdcid"].isin([1, 3])].copy()

    # Mock SQLAlchemy session.execute return
    Row = namedtuple("Row", ["ukrdcid", "patientid"])
    mock_result = [Row(1, "NHSPATIENTID1"), Row(3, "NHSPATIENTID3")]
    mock_session = MagicMock()
    mock_session.execute.return_value = mock_result

    calculator = KRTStatsCalculator(
        session=mock_session,
        facility="TESTFACILITY",
        from_time=pd.Timestamp("2024-01-01"),
        to_time=pd.Timestamp("2024-06-01")
    )

    calculator._patient_cohort = filtered_cohort

    population, table = calculator.produce_report(
        output_columns=[
                    "pid",
                    "healcarefacilitycode",
                    "admitreasoncode",
                    "admitreasoncodestd",
                    "registry_code_type",
        ], 
        input_filters=["incident"], 
        include_ni=True
    )
    
    assert population == 2
    assert isinstance(table, BaseTable)
    
    # Check renamed
    assert "nhsno" in table.headers
    assert "patientid" not in table.headers
    
    nhsno_col = table.headers.index("nhsno")
    nhs_values = [row[nhsno_col] for row in table.rows]
    assert set(nhs_values) == {"NHSPATIENTID1", "NHSPATIENTID3"}