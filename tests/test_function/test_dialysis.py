from ..utils import check_required_metadata, generate_modality_lookup, FakeDataGenerator
from ..data import DIALYSIS_COHORT_DATA, DIALYSIS_INCIDENT_PREVALENT
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ukrdc_stats.calculators.dialysis import (
    DialysisStatsCalculator,
    _calculate_frequency,
)

import pandas as pd
from pandas import Timestamp

import pytest


TEST_COHORT_SIZE = 10
START_TIME = datetime(2018, 12, 1)
END_TIME = datetime(2019, 12, 1)
FACILITY = "RFPUS"
SEED = "Avada kedavra"


@pytest.fixture(scope="function")
def ukrdc3_session_dialysis(ukrdc3_session: Session):

    # add loopup tables to database
    generate_modality_lookup(ukrdc3=ukrdc3_session)

    generator = FakeDataGenerator("moo")

    # hard code a bunch of treatments
    #FACILITY = "Hogwarts"
    for i in range(TEST_COHORT_SIZE):
        pid = generator.create_demo_patient(
            id_=i,
            sending_facility=FACILITY,
            sending_extract="UKRDC",
            ukrdc3=ukrdc3_session,
        )

        generator.generate_dialysis_treatment(
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


def test_extract_base_patient_cohort(ukrdc3_session_dialysis: Session):

    calculator = DialysisStatsCalculator(
        ukrdc3_session_dialysis, FACILITY, START_TIME, END_TIME
    )

    df = calculator._extract_base_patient_cohort()

    df_ref = pd.DataFrame(data=DIALYSIS_COHORT_DATA)

    # assert df.pid.equals(df_ref.pid)
    assert len(df) == TEST_COHORT_SIZE
    # assert df.equals(df_ref)
    for item in df.keys():
        assert df[item].equals(df_ref[item])


def test_extract_incident_prevalent(ukrdc3_session_dialysis: Session):
    calculator = DialysisStatsCalculator(
        ukrdc3_session_dialysis, FACILITY, START_TIME, END_TIME
    )

    cohort_dataframe = calculator._extract_incident_prevalent(
        pd.DataFrame(data=DIALYSIS_COHORT_DATA)
    )
    incident_prevalent = pd.DataFrame(data=DIALYSIS_INCIDENT_PREVALENT)

    assert cohort_dataframe[["prevalent", "incident"]].equals(incident_prevalent)


def test_calculate_therapies_all_patients():

    calculator = DialysisStatsCalculator(
        ukrdc3_session_dialysis, FACILITY, START_TIME, END_TIME
    )

    calculator._patient_cohort = pd.DataFrame(
        data={**DIALYSIS_COHORT_DATA, **DIALYSIS_INCIDENT_PREVALENT}
    )

    all_patients = calculator._calculate_therapies_all_patients()

    assert all_patients.data.dict() == {'x': ['HD Unknown/Incomplete', 'PD'], 'y': [2, 8], 'error_y': None}
    assert all_patients.metadata.population_size == 10


def test_calculate_therapies_incident_patients():

    calculator = DialysisStatsCalculator(
        ukrdc3_session_dialysis, FACILITY, START_TIME, END_TIME
    )

    calculator._patient_cohort = pd.DataFrame(
        data={**DIALYSIS_COHORT_DATA, **DIALYSIS_INCIDENT_PREVALENT}
    )

    incident_patients = calculator._calculate_therapies_incident_patients()

    assert incident_patients.data.dict() == {'x': ['HD Unknown/Incomplete', 'PD'], 'y': [2, 7], 'error_y': None}
    assert incident_patients.metadata.population_size == sum(DIALYSIS_INCIDENT_PREVALENT['incident'])


def test_calculate_therapies_prevalent_patients():

    calculator = DialysisStatsCalculator(
        ukrdc3_session_dialysis, FACILITY, START_TIME, END_TIME
    )

    calculator._patient_cohort = pd.DataFrame(
        data={**DIALYSIS_COHORT_DATA, **DIALYSIS_INCIDENT_PREVALENT}
    )

    prevalent_patients = calculator._calculate_therapies_prevalent_patients()

    assert prevalent_patients.data.dict() == {'x': ['PD'], 'y': [2], 'error_y': None}
    assert prevalent_patients.metadata.population_size == sum(DIALYSIS_INCIDENT_PREVALENT['prevalent'])


def test_calculate_dialysis_frequency(ukrdc3_session_dialysis: Session):
    calculator = DialysisStatsCalculator(
        ukrdc3_session_dialysis, FACILITY, START_TIME, END_TIME
    )
    calculator._patient_cohort = pd.DataFrame(
        data={**DIALYSIS_COHORT_DATA, **DIALYSIS_INCIDENT_PREVALENT}
    )

    # assert 1 == 2
    # This transformation currently happens in calculate_therapy_types (and I don't like it)
    calculator._patient_cohort.loc[
        calculator._patient_cohort.qbl05 == "HOSP", "qbl05"
    ] = "In-centre"

    # generate dialysis sessions
    generator = FakeDataGenerator("moo")
    for i, pid in enumerate(DIALYSIS_COHORT_DATA["pid"]):
        generator.generate_dialysis_session(
            id_=i,
            pid=pid,
            session_period_start=START_TIME,
            session_period_end=START_TIME + timedelta(weeks=1),
            number_of_sessions=3,
            ukrdc3=ukrdc3_session_dialysis,
        )

    dialysis_freq = calculator._calculate_dialysis_frequency()

    assert dialysis_freq.data.dict() == {
        "x": [
            "1",
            "2",
            "3",
            ">3",
        ],
        "y": [0, 0, 0, 0],
        "error_y": None,
    }


def test_calculate_access_incident(ukrdc3_session_dialysis: Session):

    calculator = DialysisStatsCalculator(
        ukrdc3_session_dialysis, FACILITY, START_TIME, END_TIME
    )
    calculator._patient_cohort = pd.DataFrame(
        data={**DIALYSIS_COHORT_DATA, **DIALYSIS_INCIDENT_PREVALENT}
    )
    patient_data = pd.DataFrame(data=DIALYSIS_COHORT_DATA)

    # generate dialysis sessions
    generator = FakeDataGenerator("moo")
    for i, row in patient_data[patient_data.registry_code_type == "HD"].iterrows():
        generator.generate_dialysis_session(
            id_=i,
            pid=row["pid"],
            session_period_start=START_TIME,
            session_period_end=START_TIME + timedelta(weeks=1),
            number_of_sessions=1,
            ukrdc3=ukrdc3_session_dialysis,
        )

    access = calculator._calculate_access_incident()

    assert access.dict()["data"] == {'x': ['AVF', 'TLN'], 'y': [1, 1], 'error_y': None}


def test_dialysis_complete_metadata(ukrdc3_session_dialysis: Session):
    calculator = DialysisStatsCalculator(
        ukrdc3_session_dialysis, FACILITY, START_TIME, END_TIME
    )
    stats = calculator.extract_stats()

    check_required_metadata(stats)
