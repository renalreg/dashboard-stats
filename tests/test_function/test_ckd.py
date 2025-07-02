import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator
from ukrdc_stats.utils import egfr
from datetime import datetime, timedelta


@pytest.fixture
def mock_cohort():
    return pd.DataFrame(
        {
            "pid": [1, 2],
            "ukrdcid": ["UKR001", "UKR002"],
            "sendingfacility": ["FAC1", "FAC1"],
            "birthtime": [datetime(1960, 1, 1), datetime(1970, 1, 1)],
            "deathtime": [None, None],
            "admitreasoncode": ["900", "901"],
            "admitreasoncodestd": ["UKKID", "UKKID"],
            "admitreasondesc": ["CKD", "CKD"],
            "fromtime": [datetime(2022, 1, 1), datetime(2022, 6, 1)],
            "totime": [None, datetime(2023, 6, 1)],
            "postcode": ["AB12 3CD", "XY98 1YZ"],
            "addressuse": ["H", "H"],
            "sex": ["1", "2"],
            "ethnicgroupcode": ["A", "B"],
            "ethnicgroupdesc": ["White", "Black"],
            "ukkaethnicity": ["White", "Black"],
        }
    )


@pytest.fixture
def mock_archive_data():
    treatments = pd.DataFrame(
        {
            "pid": [1, 2],
            "fromtime": [datetime(2022, 1, 1), datetime(2022, 6, 1)],
            "totime": [None, datetime(2023, 6, 1)],
            "admitreasoncode": ["900", "901"],
            "admitreasoncodestd": ["UKKID", "UKKID"],
            "admitreasondesc": ["CKD", "CKD"],
        }
    )
    assessments = pd.DataFrame(
        {"pid": [1, 2], "comorbidity": ["Diabetes", "Hypertension"]}
    )
    return treatments, assessments


@pytest.fixture
def mock_test_results():
    return pd.DataFrame(
        {
            "pid": [1, 2],
            "resultvalue_creat": [80, 95],
            "resultvalueunits_creat": ["umol/L", "umol/L"],
            "observationtime_creat": [datetime(2023, 1, 1), datetime(2023, 2, 1)],
        }
    )


@patch("ukrdc_stats.calculators.ckd.get_archive_session")
def test_core_query_returns_dataframe(mock_get_archive_session, mock_cohort):
    mock_get_archive_session.return_value = MagicMock()

    session = MagicMock()
    calculator = PrevalentCKDCalculator(
        session=session,
        facility="FAC1",
        prevalence_point=datetime(2023, 1, 1),
    )
    calculator._core_query = MagicMock(return_value=mock_cohort)

    df = calculator._core_query()

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    expected_columns = {
        "pid",
        "ukrdcid",
        "sendingfacility",
        "birthtime",
        "deathtime",
        "admitreasoncode",
        "admitreasoncodestd",
        "admitreasondesc",
        "fromtime",
        "totime",
        "sex",
        "postcode",
        "addressuse",
        "ethnicgroupcode",
        "ethnicgroupdesc",
        "ukkaethnicity",
    }
    assert set(df.columns) == expected_columns


@patch("ukrdc_stats.calculators.ckd.get_archive_session")
def test_extract_patient_cohort_returns_expected_columns(
    mock_get_archive_session, mock_cohort, mock_archive_data, mock_test_results
):
    mock_get_archive_session.return_value = MagicMock()

    session = MagicMock()
    calculator = PrevalentCKDCalculator(
        session=session,
        facility="FAC1",
        prevalence_point=datetime(2023, 1, 1),
    )

    calculator._core_query = MagicMock(return_value=mock_cohort)
    calculator._get_patient_numbers = MagicMock(
        return_value=pd.DataFrame(
            {
                "pid": [
                    1,
                    1,
                    2,
                ],
                "patientid": ["1234567890", "00000000", "9876543210"],
                "organization": ["NHS", "HSC", "NHS"],
                "numbertype": ["NHS", "HSC", "NHS"],
            }
        )
    )
    calculator._get_archive_data = MagicMock(return_value=mock_archive_data)
    calculator._get_test_results = MagicMock(return_value=mock_test_results)

    result = calculator.extract_patient_cohort()

    assert not result.empty
    assert "externalid" in result.columns
    assert "admitreasondesc_ukrdc" not in result.columns
    assert "calculated_egfr" in result.columns

    assert set(result["externalid"]) == {"1234567890", "9876543210"}
    assert set(result["calculated_egfr"]) == {68, 90}


def test_egfr():
    result = egfr(
        scr=100,
        scr_unit="umol/L",
        scr_date=datetime.now(),
        dob=datetime.now() - timedelta(days=365 * 40),
        sex=1,
        ethnicity="Black",
    )

    assert isinstance(result, int)
    assert result == 94

    result = egfr(
        scr=0.03,  # in g/L
        scr_unit="g/L",
        scr_date=datetime.now(),
        dob=datetime.now() - timedelta(days=365 * 40),
        sex=2,
        ethnicity="White",
    )

    assert result == 25
