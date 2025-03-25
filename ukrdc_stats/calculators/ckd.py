"""Calculators associated with ckd. In particular the care planning."""

import pandas as pd
import datetime as dt
from sqlalchemy import select, or_, create_engine, tuple_
from sqlalchemy.orm import Session, sessionmaker

from ukrdc_sqla.ukrdc import Patient, PatientRecord, Treatment, Address, PatientNumber
from ukrdc_sqla.xmlarchive import (
    Patient as XMLPatient,
    Assessment,
    Treatment as XMLTreatment,
)

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.models.generic_2d import BaseTable
from ukrdc_stats.models.base import JSONModel


def get_archive_session(session: Session) -> Session:
    # function to return a session of the xml v5 archive db
    # (xmlschemaconverter storage) not sure why this doesn't work
    db_url = session.bind.url

    password = db_url.password
    username = db_url.username
    host = db_url.host
    port = db_url.port
    drivername = db_url.drivername
    database = "removed_xml_archive"

    new_url = f"{drivername}://{username}:{password}@{host}:{port}/{database}"
    engine = create_engine(new_url)
    session = sessionmaker(bind=engine)

    with session() as archive_session:
        return archive_session


class CarePlanningReport(JSONModel):
    description: str = "prevalent ckd cohort..."
    cohort: str = "Prevalent CKD"
    table: BaseTable


class PrevalentCKDCalculator(AbstractFacilityStatsCalculator):
    def __init__(
        self,
        session: Session,
        facility: str,
        prevalence_point: dt.datetime = dt.datetime.now(),
        v5_archive_session: Session = None,
    ):
        super().__init__(session, facility)
        self._prevalence_point = prevalence_point

        if not v5_archive_session:
            self.v5_archive_session = get_archive_session(session)
        else:
            self.v5_archive_session = v5_archive_session

        # should probably be a look up against modality codes table
        self._ckd_cohort_codes = ["900", "901", "902", "903", "92", "93", "94"]

    def extract_stats(self):
        pass

    def _core_query(self):
        query_ckd_patients = (
            select(
                PatientRecord.pid,
                PatientRecord.ukrdcid,
                PatientRecord.sendingfacility,
                Patient.birthtime,
                Patient.deathtime,
                Treatment.admitreasoncode,
                Treatment.admitreasoncodestd,
                Treatment.admitreasondesc,
                Treatment.fromtime,
                Treatment.totime,
                Patient.gender.label("sex"),
                Address.postcode,
                Patient.ethnic_group_code,
                Patient.ethnic_group_code_std,
                Patient.ethnic_group_description,
            )
            .join(Treatment, Treatment.pid == PatientRecord.pid)
            .join(Patient, Patient.pid == PatientRecord.pid)
            .join(Address, Address.pid == PatientRecord.pid, isouter=True)
            .join(PatientNumber, PatientNumber.pid == PatientRecord.pid, isouter=True)
            .where(
                Treatment.admitreasoncode.in_(self._ckd_cohort_codes),
                Treatment.fromtime < self._prevalence_point,
                or_(
                    Treatment.totime > self._prevalence_point,
                    Treatment.totime.is_(None),
                ),
                or_(
                    Patient.deathtime > self._prevalence_point,
                    Patient.deathtime.is_(None),
                ),
                Address.addressuse == "H",
                PatientRecord.sendingfacility == self.facility,
                PatientRecord.sendingextract == "UKRDC",
            )
            .order_by(PatientRecord.pid)
        )

        base_cohort = (
            pd.DataFrame(self.session.execute(query_ckd_patients))
            .drop_duplicates()
            .reset_index(drop=True)
        )

        return base_cohort

    def _get_patient_numbers(self, pids: list[str]) -> pd.DataFrame:
        query = (
            select(
                PatientNumber.pid,
                PatientNumber.patientid,
                PatientNumber.organization,
                PatientNumber.numbertype,
            )
            .distinct(
                PatientNumber.pid,
                PatientNumber.patientid,
                PatientNumber.organization,
                PatientNumber.numbertype,
            )
            .where(
                PatientNumber.pid.in_(pids),
            )
        )

        patients_numbers = pd.DataFrame(self.session.execute(query))

        return patients_numbers.reset_index(drop=True).astype(str)

    def _get_archive_data(self, patient_numbers: pd.DataFrame):
        assessments_query = (
            select(
                XMLPatient.nationalid.label("patientid"),
                XMLPatient.organization,
                XMLPatient.numbertype,
                XMLPatient.creation_date,
                Assessment.assessmentstart,
                Assessment.assessmentend,
                Assessment.assessmenttypecode,
                Assessment.assessmenttypecodestd,
                Assessment.assessmenttypecodedesc,
                Assessment.assessmentoutcomecode,
                Assessment.assessmentoutcomecodestd,
                Assessment.assessmentoutcomecodedesc,
            )
            .join(
                Assessment,
                Assessment.patientid == XMLPatient.id,
            )
            .where(
                Assessment.assessmentstart < self._prevalence_point,
                tuple_(
                    XMLPatient.nationalid,
                    XMLPatient.organization,
                    XMLPatient.numbertype,
                ).in_(
                    list(
                        zip(
                            patient_numbers["patientid"],
                            patient_numbers["organization"],
                            patient_numbers["numbertype"],
                        )
                    )
                ),
            )
        )

        treatments_query = (
            select(
                XMLPatient.nationalid.label("patientid"),
                XMLPatient.organization,
                XMLPatient.numbertype,
                XMLPatient.creation_date,
                XMLTreatment.admitreasoncode,
                XMLTreatment.admitreasoncodestd,
                XMLTreatment.admitreasondesc,
                XMLTreatment.fromtime,
                XMLTreatment.totime,
            )
            .join(
                XMLTreatment,
                XMLTreatment.patientid == XMLPatient.id,
            )
            .where(
                XMLTreatment.fromtime < self._prevalence_point,
                or_(
                    XMLTreatment.totime > self._prevalence_point,
                    XMLTreatment.totime.is_(None),
                ),
                XMLTreatment.admitreasoncode.in_(self._ckd_cohort_codes),
                tuple_(
                    XMLPatient.nationalid,
                    XMLPatient.organization,
                    XMLPatient.numbertype,
                ).in_(
                    list(
                        zip(
                            patient_numbers["patientid"],
                            patient_numbers["organization"],
                            patient_numbers["numbertype"],
                        )
                    )
                ),
            )
        )

        assessments = pd.DataFrame(
            self.v5_archive_session.execute(assessments_query)
        ).reset_index(drop=True)
        treatments = pd.DataFrame(
            self.v5_archive_session.execute(treatments_query)
        ).reset_index(drop=True)

        # drop ids and deduplicate (incase same patient has been written multiple times)
        assessments = pd.merge(
            assessments,
            patient_numbers,
            on=["patientid", "organization", "numbertype"],
            how="inner",
        )
        treatments = pd.merge(
            treatments,
            patient_numbers,
            on=["patientid", "organization", "numbertype"],
            how="inner",
        )

        assessments = assessments.drop(
            columns=["patientid", "organization", "numbertype"]
        ).drop_duplicates()
        treatments = treatments.drop(
            columns=["patientid", "organization", "numbertype"]
        ).drop_duplicates()

        return treatments, assessments

    def _get_test_results(self, patient_ids):
        """gets the most recent creatinine and lab egfr

        Args:
            patient_ids (_type_): _description_
        """
        return pd.DataFrame([], columns=["pid", "creat", "egfr"])

    def _extract_base_patient_cohort(self):
        # Get main cohort from ukrdc
        cohort = self._core_query()

        if cohort.empty:
            return

        # Get all know patient identifiers for matching
        patient_numbers = self._get_patient_numbers(cohort["pid"].tolist())

        # Send patient numbers to the archive to extract data from there
        treatments, assessments = self._get_archive_data(patient_numbers)

        # correct the treatments using the archive data
        # we assume treatments without corresponding ukrdc record are invalid
        # this could/should be restricted to codes that can map to eachother
        # e.g. 902 -> 900 where like '9%' or something
        cohort = pd.merge(
            cohort,
            treatments,
            on=["pid", "fromtime", "totime"],
            how="left",
            suffixes=("_ukrdc", ""),
        )

        # add in treatments not in the archive and drop ukrdc values
        ukrdc_only = cohort["admitreasoncode"].isnull()
        cohort.loc[
            ukrdc_only, ["admitreasoncode", "admitreasoncodestd", "admitreasondesc"]
        ] = cohort.loc[
            ukrdc_only,
            [
                "admitreasoncode_ukrdc",
                "admitreasoncodestd_ukrdc",
                "admitreasondesc_ukrdc",
            ],
        ].values
        cohort = cohort.drop(
            columns=[
                "admitreasoncode_ukrdc",
                "admitreasoncodestd_ukrdc",
                "admitreasondesc_ukrdc",
            ]
        )

        # join assessments
        cohort = pd.merge(
            cohort,
            assessments,
            on=["pid"],
            how="left",
            suffixes=("_treatment", "_assessment"),
        )

        test_results = self._get_test_results(cohort["pid"].tolist())

        # get test results
        cohort = pd.merge(
            cohort,
            test_results,
            on=["pid"],
            how="left",
        )

        return cohort

    def extract_patient_cohort(self):
        self._patient_cohort = self._extract_base_patient_cohort()
        return self._patient_cohort
