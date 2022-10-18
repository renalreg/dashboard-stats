import pytest
from sqlalchemy.orm import Session

from ukrdc_stats.demographics import DemographicsCalculator

from ..utils import create_demo_patient

TEST_COHORT_SIZE = 20


@pytest.fixture(scope="function")
def ukrdc3_session_demographics(ukrdc3_session: Session):
    for i in range(TEST_COHORT_SIZE):
        create_demo_patient(i, "FACILITY_1", "UKRDC", ukrdc3_session)
    ukrdc3_session.commit()
    return ukrdc3_session


def test_extract_base_patient_cohort(ukrdc3_session_demographics: Session):
    calculator = DemographicsCalculator(ukrdc3_session_demographics, "FACILITY_1")

    df = calculator._extract_base_patient_cohort()
    assert len(df) == TEST_COHORT_SIZE

    calculator.extract_patient_cohort()
    assert calculator._patient_cohort is not None
    assert calculator._patient_cohort.equals(df)


def test_calculate_gender(ukrdc3_session_demographics: Session):
    calculator = DemographicsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    calculator.extract_patient_cohort()

    g = calculator._calculate_gender()
    assert g.dict() == {
        "metadata": {
            "title": "Gender Distribution",
            "axis_titles": {"x": "Gender", "y": "No. of Patients"},
            "coding_standard_x": "NHS_DATA_DICTIONARY",
            "units_y": None,
        },
        "data": {"x": ["0", "1", "2", "9"], "y": [4, 4, 8, 4], "error_y": None},
    }


def test_calculate_ethnic_group_code(ukrdc3_session_demographics: Session):
    calculator = DemographicsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    calculator.extract_patient_cohort()

    g = calculator._calculate_ethnic_group_code()
    assert g.dict() == {
        "metadata": {
            "title": "Ethnic Group",
            "axis_titles": {"x": "Ethnicity", "y": "No. of Patients"},
            "coding_standard_x": "NHS_DATA_DICTIONARY",
            "units_y": None,
        },
        "data": {
            "x": ["99", "A", "D", "E", "F", "H", "J", "K", "L", "M", "N", "R", "S"],
            "y": [3, 1, 1, 1, 1, 1, 2, 1, 2, 2, 2, 1, 2],
            "error_y": None,
        },
    }


def test_calculate_age(ukrdc3_session_demographics: Session):
    calculator = DemographicsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    calculator.extract_patient_cohort()

    g = calculator._calculate_age()
    assert g.dict() == {
        "metadata": {
            "title": "Age Distribution",
            "axis_titles": {"x": "Age", "y": "No. of Patients"},
            "coding_standard_x": None,
            "units_y": None,
        },
        "data": {
            "x": [
                "12",
                "16",
                "19",
                "20",
                "26",
                "27",
                "32",
                "34",
                "46",
                "47",
                "49",
                "54",
                "59",
                "63",
                "69",
            ],
            "y": [1, 1, 2, 1, 1, 1, 2, 2, 1, 1, 1, 1, 2, 1, 2],
            "error_y": None,
        },
    }


def test_extract_stats(ukrdc3_session_demographics: Session):
    calculator = DemographicsCalculator(ukrdc3_session_demographics, "FACILITY_1")
    stats = calculator.extract_stats()

    # Test most basic composite stats
    assert stats.metadata.population == TEST_COHORT_SIZE
