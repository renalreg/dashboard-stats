from datetime import datetime
import pytest
from sqlalchemy.orm import Session
from freezegun import freeze_time

from ukrdc_stats import DemographicStatsCalculator

from ..utils import check_required_metadata, FakeDataGenerator

TEST_COHORT_SIZE = 20
TEST_TIME = datetime(2022, 11, 22)


@pytest.fixture(scope="function")
def ukrdc3_session_demographics(ukrdc3_session: Session):
    generator = FakeDataGenerator("moo")

    for i in range(TEST_COHORT_SIZE):
        generator.create_demo_patient(i, "FACILITY_1", "UKRDC", ukrdc3_session)
    ukrdc3_session.commit()
    return ukrdc3_session


@freeze_time(TEST_TIME)
def test_extract_base_patient_cohort(ukrdc3_session_demographics: Session):
    calculator = DemographicStatsCalculator(ukrdc3_session_demographics, "FACILITY_1")

    df = calculator._extract_base_patient_cohort()
    assert len(df) == TEST_COHORT_SIZE

    calculator.extract_patient_cohort()
    assert calculator._patient_cohort is not None
    assert calculator._patient_cohort.equals(df)


@freeze_time(TEST_TIME)
def test_calculate_gender(ukrdc3_session_demographics: Session):
    calculator = DemographicStatsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    calculator.extract_patient_cohort()

    g = calculator._calculate_gender()

    assert g.dict() == {
        "metadata": {
            "title": "Gender Distribution",
            "summary": "",
            "description": "",
            "axis_titles": {"x": "Gender", "y": "No. of Patients"},
            "coding_standard_x": None,
            "units_y": None,
        },
        "data": {
            "x": ["Female", "Indeterminate", "Male"],
            "y": [8, 3, 4],
            "error_y": None,
        },
    }


@freeze_time(TEST_TIME)
def test_calculate_ethnic_group_code(ukrdc3_session_demographics: Session):
    calculator = DemographicStatsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    calculator.extract_patient_cohort()

    g = calculator._calculate_ethnic_group_code()
    assert g.dict() == {
        "metadata": {
            "title": "Ethnic Group",
            "summary": "",
            "description": "",
            "axis_titles": {"x": "Ethnicity", "y": "No. of Patients"},
            "coding_standard_x": None,
            "units_y": None,
        },
        "data": {
            "x": ["Asian", "Black", "Mixed", "Not Stated", "Other", "White"],
            "y": [6, 3, 4, 2, 1, 4],
            "error_y": None,
        },
    }


@freeze_time(TEST_TIME)
def test_calculate_age(ukrdc3_session_demographics: Session):
    calculator = DemographicStatsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    calculator.extract_patient_cohort()

    g = calculator._calculate_age()

    assert g.dict() == {
        "metadata": {
            "title": "Age Distribution",
            "summary": "",
            "description": "",
            "axis_titles": {"x": "Age", "y": "No. of Patients"},
            "coding_standard_x": None,
            "units_y": None,
        },
        "data": {
            "x": [
                "12",
                "22",
                "23",
                "27",
                "28",
                "29",
                "31",
                "35",
                "39",
                "42",
                "43",
                "45",
                "48",
                "49",
                "50",
                "55",
                "57",
                "58",
                "61",
                "68",
            ],
            "y": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            "error_y": None,
        },
    }


@freeze_time(TEST_TIME)
def test_extract_stats(ukrdc3_session_demographics: Session):
    calculator = DemographicStatsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    stats = calculator.extract_stats()

    # Test most basic composite stats
    assert stats.metadata.population == TEST_COHORT_SIZE


@freeze_time(TEST_TIME)
def test_demographics_complete_metadata(ukrdc3_session_demographics: Session):
    calculator = DemographicStatsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    stats = calculator.extract_stats()

    check_required_metadata(stats)
