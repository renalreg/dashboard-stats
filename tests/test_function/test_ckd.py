import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator, Boolean
from sqlalchemy.dialects.mysql import BIT as MySQL_BIT
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator
from ukrdc_sqla.ukrdc import (
    PatientRecord,
    Patient,
    Treatment,
    Address,
    CodeMap,
    PatientNumber,
    ModalityCodes,
)
from ukrdc_sqla.xmlarchive import (
    Patient as XMLPatient,
    Assessment,
    Treatment as XMLTreatment,
)


class SQLiteSafeBIT(TypeDecorator):
    impl = Boolean

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Boolean)
        else:
            return dialect.type_descriptor(MySQL_BIT(1))


# Sqlite doesn't support BIT, so we need to monkey patch it
def patch_modality_bit_columns():
    for colname in [
        "acute",
        "transfer_in",
        "ckd",
        "cons",
        "rrt",
        "end_of_care",
        "is_imprecise",
        "transfer_out",
    ]:
        col = ModalityCodes.__table__.c[colname]
        col.type = SQLiteSafeBIT()


@pytest.fixture
def archive_session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    XMLPatient.__table__.create(bind=engine)
    XMLTreatment.__table__.create(bind=engine)
    Assessment.__table__.create(bind=engine)
    yield session
    session.close()


@pytest.fixture
def populated_archive(archive_session):
    archive_session.add_all(
        [
            XMLPatient(
                id=1,
                sendingfacility="FAC1",
                nationalid="123",
                organization="NHS",
                numbertype="NHS",
                creation_date=datetime.now(),
            ),
            XMLPatient(
                id=2,
                sendingfacility="FAC1",
                nationalid="456",
                organization="NHS",
                numbertype="NHS",
                creation_date=datetime.now(),
            ),
        ]
    )

    # Add treatments
    archive_session.add_all(
        [
            XMLTreatment(
                patientid=1,
                fromtime=datetime(2022, 1, 1),
                totime=datetime(2024, 1, 1),
                admitreasoncode="900",
                admitreasoncodestd="UKKID",
                admitreasondesc="CKD",
                creation_date=datetime.now(),
            ),
            XMLTreatment(
                patientid=2,
                fromtime=datetime(2022, 1, 1),
                totime=datetime(2024, 1, 1),
                admitreasoncode="80",
                admitreasoncodestd="UKKID",
                admitreasondesc="RRT",
                creation_date=datetime.now(),
            ),
            XMLTreatment(
                patientid=1,
                fromtime=datetime(2025, 1, 1),
                totime=datetime(2026, 1, 1),
                admitreasoncode="900",
                admitreasoncodestd="UKKID",
                admitreasondesc="CKD",
                creation_date=datetime.now(),
            ),
        ]
    )

    archive_session.commit()


@pytest.fixture
def mock_patient_numbers():
    return pd.DataFrame(
        {
            "patientid": ["123"],
            "organization": ["NHS"],
            "numbertype": ["NHS"],
            "pid": [1],
        }
    )


@pytest.fixture
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    PatientRecord.__table__.create(bind=engine)
    Patient.__table__.create(bind=engine)
    Treatment.__table__.create(bind=engine)
    Address.__table__.create(bind=engine)
    CodeMap.__table__.create(bind=engine)
    PatientNumber.__table__.create(bind=engine)
    patch_modality_bit_columns()
    ModalityCodes.__table__.create(bind=engine)
    yield session
    session.close()


@pytest.fixture
def populated_patient(sqlite_session):
    pid = 1

    # Add mock patients
    sqlite_session.add_all(
        [
            PatientRecord(
                pid=1,
                sendingfacility="FAC1",
                sendingextract="UKRDC",
                localpatientid="XYZ123",
                repositorycreationdate=datetime.now(),
                repositoryupdatedate=datetime.now(),
                creation_date=datetime.now(),
            ),
            Patient(
                pid=1,
                birthtime=datetime(1960, 1, 1),
                deathtime=None,
                gender="1",
                ethnicgroupcode="A",
                ethnicgroupdesc="White",
                ethnicgroupcodestd="ABC",
                creation_date=datetime.now(),
            ),
            Address(
                id=1,
                pid=1,
                postcode="AB12 3CD",
                addressuse="H",
                creation_date=datetime.now(),
            ),
            CodeMap(
                source_code="A",
                source_coding_standard="ABC",
                destination_code="W",
                destination_coding_standard="URTS_ETHNIC_GROUPING",
                update_date=None,
                creation_date=datetime.now(),
            ),
            PatientNumber(
                id=1,
                pid=1,
                patientid="1234567890",
                organization="NHS",
                numbertype="NHS",
                creation_date=datetime.now(),
            ),
            ModalityCodes(
                registry_code="900",
                registry_code_type="CK",
                acute=False,
                transfer_in=False,
                ckd=False,
                cons=False,
                rrt=False,
                end_of_care=False,
                is_imprecise=False,
            ),
        ]
    )

    # 3 treatments
    sqlite_session.add_all(
        [
            Treatment(
                id=1,
                pid=pid,
                admitreasoncode="900",
                admitreasoncodestd="UKKID",
                admitreasondesc="CKD",
                fromtime=datetime(2020, 1, 1),
                totime=datetime(2024, 1, 1),
                creation_date=datetime.now(),
            ),
            Treatment(
                id=2,
                pid=pid,
                admitreasoncode="900",
                admitreasoncodestd="UKKID",
                admitreasondesc="CKD",
                fromtime=datetime(2022, 6, 1),
                totime=None,
                creation_date=datetime.now(),
            ),
            Treatment(
                id=3,
                pid=pid,
                admitreasoncode="900",
                admitreasoncodestd="UKKID",
                admitreasondesc="CKD",
                fromtime=datetime(2023, 6, 1),
                totime=datetime(2024, 6, 1),
                creation_date=datetime.now(),
            ),
        ]
    )

    sqlite_session.commit()
    return pid


def test_core_query(sqlite_session, populated_patient):
    prevalence_point = datetime(2023, 1, 1)
    calculator = PrevalentCKDCalculator(
        session=sqlite_session,
        facility="FAC1",
        prevalence_point=prevalence_point,
        v5_archive_session=archive_session,
    )
    calculator._ckd_cohort_codes = ["900"]

    # Unfiltered — should return all 3 treatments
    df_all = calculator._core_query(extract_all=True)
    assert len(df_all) == 3

    # Filtered - should return treatments with ids 1 and 2, since 3 is after prevalence point
    df_filtered = calculator._core_query(extract_all=False)
    assert len(df_filtered) == 2
    assert not df_filtered["fromtime"].isin([datetime(2023, 6, 1)]).any()


def test_get_archive_data(archive_session, populated_archive, mock_patient_numbers):
    calculator = PrevalentCKDCalculator(
        session=archive_session,
        v5_archive_session=archive_session,
        facility="FAC1",
        prevalence_point=datetime(2023, 1, 1),
    )
    calculator._ckd_not_rrt_codes = ["900"]  # Only include this

    treatments, assessments = calculator._get_archive_data(mock_patient_numbers)

    assert isinstance(treatments, pd.DataFrame)
    assert not treatments.empty
    assert all(treatments["admitreasoncode"] == "900")

    assert len(treatments) == 1
    assert isinstance(assessments, pd.DataFrame)
    assert assessments.empty

    treatments, assessments = calculator._get_archive_data(mock_patient_numbers, True)
    # Select all, meaning even the ones not on prevalence_point should get returned
    assert len(treatments) == 2
    assert all(treatments["admitreasoncode"] == "900")


def test_extract_base_patient_cohort(
    sqlite_session, archive_session, populated_patient, populated_archive
):
    prevalence_point = datetime(2023, 1, 1)
    calculator = PrevalentCKDCalculator(
        session=sqlite_session,
        v5_archive_session=archive_session,
        facility="FAC1",
        prevalence_point=prevalence_point,
    )
    calculator._ckd_cohort_codes = ["900"]
    calculator._ckd_not_rrt_codes = ["900"]

    calculator._get_test_results = MagicMock(
        return_value=pd.DataFrame(
            {
                "pid": [1],
                "resultvalue_creat": [80],
                "resultvalueunits_creat": ["umol/L"],
                "observationtime_creat": [datetime(2022, 12, 1)],
            }
        ).astype({"pid": str})
    )

    cohort = calculator._extract_base_patient_cohort()

    assert isinstance(cohort, pd.DataFrame)
    assert not cohort.empty

    expected_cols = {
        "ukrdcid",
        "pid",
        "admitreasoncode",
        "calculated_egfr",
        "externalid",
    }
    assert expected_cols.issubset(set(cohort.columns))

    assert len(cohort) == 2
    assert (cohort["pid"] == "1").all()
    assert (cohort["admitreasoncode"] == "900").all()
    assert cohort["calculated_egfr"][0] == 90

    cohort = calculator._extract_base_patient_cohort(extract_all=True)
    assert len(cohort) == 3
