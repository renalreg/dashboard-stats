from tracemalloc import start
from typing_extensions import assert_type
from unittest import TestCase
from ..utils import create_demo_patient, generate_treatment, generate_dialysis_session
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ukrdc_stats.calculators.dialysis import (
    DialysisStatsCalculator,
    _calculate_frequency,
)


import pandas as pd
from pandas import Timestamp

import pytest

# debug dependancies
from ukrdc_sqla.ukrdc import DialysisSession
from sqlalchemy import select


TEST_COHORT_SIZE = 20
START_TIME = datetime(2018, 12, 1)
END_TIME = datetime(2019, 12, 1)
FACILITY = "Hogwarts"
SEED = "Avada kedavra"


# data to create _patient_cohort dataframe from (and to check the functions which query the database against)
DATA = {
    "ukrdcid": [
        "ukrdc_test:2",
        "ukrdc_test:3",
        "ukrdc_test:6",
        "ukrdc_test:7",
        "ukrdc_test:12",
        "ukrdc_test:13",
        "ukrdc_test:18",
    ],
    "pid": ["test:2", "test:3", "test:6", "test:7", "test:12", "test:13", "test:18"],
    "admitreasoncode": ["3", "5", "11", "12", "5", "2", "11"],
    "qbl05": ["HOSP", "HOME", None, None, "HOME", "HOSP", None],
    "hdp04": [None, None, None, None, None, None, None],
    "fromtime": [
        Timestamp("2018-12-01 00:00:00"),
        Timestamp("2018-12-15 00:00:00"),
        Timestamp("2018-12-15 00:00:00"),
        Timestamp("2018-12-15 00:00:00"),
        Timestamp("2018-12-15 00:00:00"),
        Timestamp("2018-12-15 00:00:00"),
        Timestamp("2018-12-15 00:00:00"),
    ],
    "totime": [
        Timestamp("2019-12-01 00:00:00"),
        Timestamp("2019-12-01 00:00:00"),
        Timestamp("2019-12-15 00:00:00"),
        Timestamp("2019-12-15 00:00:00"),
        Timestamp("2019-12-15 00:00:00"),
        Timestamp("2019-12-15 00:00:00"),
        Timestamp("2019-12-01 00:00:00"),
    ],
    "deathtime": [None, None, None, None, None, None, None],
    "death": [None, None, None, None, None, None, None],
}

INCIDENT_PREVALENT = {
    "prevalent": [False, False, True, True, True, True, False],
    "incident": [False, True, True, True, True, True, True],
}


@pytest.fixture(scope="function")
def ukrdc3_session_demographics(ukrdc3_session: Session):
    # hard code a bunch of treatments
    FACILITY = "Hogwarts"
    for i in range(TEST_COHORT_SIZE):
        pid = create_demo_patient(
            id_=i,
            sending_facility=FACILITY,
            sending_extract="UKRDC",
            ukrdc3=ukrdc3_session,
        )
        print(pid)
        generate_treatment(
            id_=i,
            pid=pid,
            health_care_facility=FACILITY,
            start_time=START_TIME,
            end_time=END_TIME,
            ukrdc3=ukrdc3_session,
        )

    ukrdc3_session.commit()
    return ukrdc3_session


def test_calculate_frequency():
    start_date = datetime(1984, 1, 1)
    end_date = datetime(1984, 1, 8)
    freq = _calculate_frequency(start_date, end_date, 1)

    assert freq == 1.0


def test_extract_base_patient_cohort(ukrdc3_session_demographics: Session):

    calculator = DialysisStatsCalculator(
        ukrdc3_session_demographics, FACILITY, START_TIME, END_TIME
    )

    df = calculator._extract_base_patient_cohort()

    df_ref = pd.DataFrame(data=DATA)

    assert df.pid.equals(df_ref.pid)

    assert len(df) == 7
    assert df.equals(df_ref)


def test_extract_incident_prevalent(ukrdc3_session_demographics: Session):
    calculator = DialysisStatsCalculator(
        ukrdc3_session_demographics, FACILITY, START_TIME, END_TIME
    )

    cohort_dataframe = calculator._extract_incident_prevalent(pd.DataFrame(data=DATA))
    incident_prevalent = pd.DataFrame(data=INCIDENT_PREVALENT)

    assert cohort_dataframe[["prevalent", "incident"]].equals(incident_prevalent)


def test_calculate_all_home_therapies():

    calculator = DialysisStatsCalculator(
        ukrdc3_session_demographics, FACILITY, START_TIME, END_TIME
    )

    calculator._patient_cohort = pd.DataFrame(data={**DATA, **INCIDENT_PREVALENT})

    all_home = calculator._calculate_all_home_therapies()

    assert all_home.dict() == {
        "metadata": {
            "title": "Proportion of all Dialysis Patients on Home Therapies",
            "summary": "",
            "description": "",
            "total_population": None,
        },
        "node": {
            "node_labels": [
                "Haemodialysis",
                "Peritoneal dialysis",
                "Home therapies",
                "In-centre therapies",
                "Incomplete/Not given",
            ]
        },
        "link": {
            "source": ["0", "0", "0", "1"],
            "target": ["2", "3", "4", "2"],
            "value": ["2", "2", "0", "3"],
        },
    }


def test_calculate_incident_home_therapies():

    calculator = DialysisStatsCalculator(
        ukrdc3_session_demographics, FACILITY, START_TIME, END_TIME
    )

    calculator._patient_cohort = pd.DataFrame(data={**DATA, **INCIDENT_PREVALENT})

    incident_home = calculator._calculate_incident_home_therapies()

    assert incident_home.dict() == {
        "metadata": {
            "title": "Proportion of Incident Patients on Home Therapies",
            "summary": "",
            "description": "",
            "total_population": None,
        },
        "node": {
            "node_labels": [
                "Haemodialysis",
                "Peritoneal dialysis",
                "Home therapies",
                "In-centre therapies",
                "Incomplete/Not given",
            ]
        },
        "link": {
            "source": ["0", "0", "0", "1"],
            "target": ["2", "3", "4", "2"],
            "value": ["2", "1", "0", "3"],
        },
    }


def test_calculate_prevalent_home_therapies():

    calculator = DialysisStatsCalculator(
        ukrdc3_session_demographics, FACILITY, START_TIME, END_TIME
    )

    calculator._patient_cohort = pd.DataFrame(data={**DATA, **INCIDENT_PREVALENT})

    prevalent_home = calculator._calculate_prevalent_home_therapies()

    assert prevalent_home.dict() == {
        "metadata": {
            "title": "Proportion of Prevalent Patients on Home Therapies",
            "summary": "",
            "description": "",
            "total_population": None,
        },
        "node": {
            "node_labels": [
                "Haemodialysis",
                "Peritoneal dialysis",
                "Home therapies",
                "In-centre therapies",
                "Incomplete/Not given",
            ]
        },
        "link": {
            "source": ["0", "0", "0", "1"],
            "target": ["2", "3", "4", "2"],
            "value": ["1", "1", "0", "2"],
        },
    }


def test_calculate_dialysis_frequency(ukrdc3_session_demographics: Session):
    calculator = DialysisStatsCalculator(
        ukrdc3_session_demographics, FACILITY, START_TIME, END_TIME
    )
    calculator._patient_cohort = pd.DataFrame(data={**DATA, **INCIDENT_PREVALENT})

    average_sessions = 3
    patient_data = pd.DataFrame(data=DATA)

    # generate dialysis sessions
    for i, row in patient_data[
        patient_data.admitreasoncode.isin(["1", "2", "3", "5"])
    ].iterrows():
        generate_dialysis_session(
            id_=i,
            pid=row["pid"],
            session_period_start=START_TIME,
            session_period_end=START_TIME + timedelta(weeks=1),
            number_of_sessions=average_sessions,
            ukrdc3=ukrdc3_session_demographics,
        )

    dialysis_freq = calculator._calculate_dialysis_frequency()

    assert dialysis_freq.dict() == {
        "metadata": {
            "title": "In-Centre Dialysis Frequency",
            "summary": "",
            "description": "",
            "axis_titles": {"x": "Frequency (days per week)", "y": "No. of Patients"},
            "coding_standard_x": None,
            "units_y": None,
        },
        "data": {
            "x": [
                "0.0- 0.5",
                "0.5- 1.0",
                "1.0- 1.5",
                "1.5- 2.0",
                "2.0- 2.5",
                "2.5- 3.0",
                "3.0- 3.5",
                "3.5- 4.0",
                "4.0- 4.5",
                "4.5- 5.0",
                "5.0- 5.5",
                "5.5- 6.0",
                "6.0- 6.5",
                "6.5- 7.0",
            ],
            "y": [0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0],
            "error_y": None,
        },
    }


def test_calculate_access_incident(ukrdc3_session_demographics: Session):

    calculator = DialysisStatsCalculator(
        ukrdc3_session_demographics, FACILITY, START_TIME, END_TIME
    )
    calculator._patient_cohort = pd.DataFrame(data={**DATA, **INCIDENT_PREVALENT})
    patient_data = pd.DataFrame(data=DATA)

    average_sessions = 1
    # generate dialysis sessions
    for i, row in patient_data[
        patient_data.admitreasoncode.isin(["1", "2", "3", "5"])
    ].iterrows():
        generate_dialysis_session(
            id_=i,
            pid=row["pid"],
            session_period_start=START_TIME,
            session_period_end=START_TIME + timedelta(weeks=1),
            number_of_sessions=average_sessions,
            ukrdc3=ukrdc3_session_demographics,
        )

    access = calculator._calculate_access_incident()
    assert access.dict() == {
        "metadata": {
            "title": "Initial Vascular Access of Incident Patients",
            "summary": "",
            "description": "",
            "axis_titles": {"x": "Line Type", "y": "No. of Patients"},
            "coding_standard_x": None,
            "units_y": None,
        },
        "data": {"x": ["NLN", "TLN"], "y": [1, 2], "error_y": None},
    }
