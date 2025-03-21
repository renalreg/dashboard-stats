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
    # function to yield session of the xml v5 archive db
    # (xmlschemaconverter storage) not sure why this doesn't work

    archive_db_name = "removed_xml_archive"
    archive_db_url = str(session.bind.url).replace(
        session.bind.url.database, archive_db_name
    )
    engine = create_engine(archive_db_url)
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

        base_cohort = pd.DataFrame(
            self.session.execute(query_ckd_patients)
        ).reset_index(drop=True)

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
        query = (
            select(
                XMLPatient.nationalid,
                XMLPatient.organization,
                XMLPatient.numbertype,
                XMLTreatment.admitreasoncode,
                XMLTreatment.fromtime,
                XMLTreatment.totime,
            )
            .join(XMLTreatment, XMLTreatment.patientid == XMLPatient.id, isouter=True)
            .join(Assessment, Assessment.patientid == XMLPatient.id, isouter=True)
            .where(
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
                XMLTreatment.admitreasoncode.in_(self._ckd_cohort_codes),
                XMLTreatment.fromtime < self._prevalence_point,
                or_(
                    XMLTreatment.totime > self._prevalence_point,
                    XMLTreatment.totime.is_(None),
                ),
            )
        )

        archive_cohort = pd.DataFrame(self.v5_archive_session.execute(query))

        # join the pid back in with a merge
        archive_cohort = archive_cohort.rename(columns={"nationalid": "patientid"})
        archive_cohort = pd.merge(
            archive_cohort,
            patient_numbers,
            on=["patientid", "organization", "numbertype"],
        )

        return archive_cohort

    def extract_patient_cohort(self):
        # Get main cohort from ukrdc
        self._patient_cohort = self._core_query()

        if self._patient_cohort.empty:
            return

        # Get all know patient identifiers for matching
        patient_numbers = self._get_patient_numbers(
            self._patient_cohort["pid"].tolist()
        )

        # Send patient numbers to the archive to extract data from there
        self._archive_cohort = self._get_archive_data(patient_numbers)

        # now we combine the three dataframes in accordance with the
        # specification

        pass
