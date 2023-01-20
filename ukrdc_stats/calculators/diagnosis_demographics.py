"""
Patient cohort demographics stats calculator
"""

import datetime as dt
from typing import Dict, Optional
from pydantic import Field

import pandas as pd
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import Patient, PatientRecord, RenalDiagnosis

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError
from ukrdc_stats.utils import age_from_dob

from ..descriptions import demographic_descriptions
from ..code_groupings import ETHNIC_GROUP_MAP, GENDER_GROUP_MAP, PRD_CODE_MAP
from ..models.base import JSONModel
from ..models.maps import (
    DoubleLabelled3d,
    Basic3dMetadata,
    AxisLabel3d,
    DoubleLabelled3dData,
)


class DemographicsMetadata(JSONModel):
    population: Optional[int] = Field(
        None, description="Population demographics are calculated from"
    )


class DemographicsStats(JSONModel):
    gender: DoubleLabelled3d = Field(..., description="Gender PRD demographic stats")
    ethnic_group: DoubleLabelled3d = Field(
        ..., description="Ethnic group PRD demographic stats"
    )
    age: DoubleLabelled3d = Field(..., description="Age PRD demographic stats")
    metadata: DemographicsMetadata = Field(
        ..., description="Metadata describing demographic stats"
    )


def calculate_base_patient_histogram_3D(
    cohort: pd.DataFrame, group: str, code_map: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """Extract a histogram of the patient cohort, grouped by the given column

    Args:
        cohort (pd.DataFrame): Patient cohort
        group (str): Column to group bys

    Raises:
        NoCohortError: If the patient cohort is empty

    Returns:
        pd.DataFrame: Histogram dataframe of the patient cohort
    """

    if code_map:
        mapped_column = f"{group}_mapped"
        cohort[mapped_column] = cohort[group].map(code_map)

        histogram = (
            cohort[["ukrdcid", mapped_column, "PRD"]]
            .drop_duplicates()
            .groupby([mapped_column, "PRD"])
            .count()
            .reset_index()
        )

    else:
        histogram = (
            cohort[["ukrdcid", group, "PRD"]]
            .drop_duplicates()
            .groupby([group, "PRD"])
            .count()
            .reset_index()
        )

    return histogram.rename(columns={"ukrdcid": "Count"})


class RenalDiagnosisStatsCalculator(AbstractFacilityStatsCalculator):
    """Calculates the demographics information based on the personal information listed in the patient table"""

    def __init__(
        self, session: Session, facility: str, date: Optional[dt.datetime] = None
    ):
        """Initialises the PatientDemographicStats class and immediately runs the relevant query

        Args:
            session (SQLAlchemy session): Connection to database to calculate statistic from.
            facility (str): Facility to calculate the
            date (datetime, optional): Date to calculate at. Defaults to today.
        """
        super().__init__(session, facility)

        # Set the date to calculate at, defaulting to today
        self.date: dt.datetime = date or dt.datetime.today()

    def _extract_base_patient_cohort(
        self,
        include_tracing: Optional[bool] = False,
        limit_to_ukrdc: Optional[bool] = True,
        limit_query_length: Optional[int] = None,
    ) -> pd.DataFrame:
        """Main database queries to produce a dataframe containing the patient demographics
        for a specified Unit.

        Args:
            include_tracing (bool, optional): Switch to use tracing rec. Defaults to False.

        Returns:
            pd.DataFrame: _description_
        """

        # select all patients who have a patientrecord sent from the facility
        patient_query = (
            select(
                PatientRecord.ukrdcid,
                Patient.gender,
                Patient.ethnic_group_code,
                RenalDiagnosis.diagnosis_code,
                RenalDiagnosis.diagnosis_code_std,
                Patient.birth_time,
                Patient.death_time,
            )  # type:ignore
            .join(PatientRecord, Patient.pid == PatientRecord.pid)  # type:ignore
            .join(RenalDiagnosis, RenalDiagnosis.pid == PatientRecord.pid)
            .where(
                and_(
                    PatientRecord.sendingfacility == self.facility,
                    or_(
                        Patient.death_time.is_(None), Patient.death_time > self.date
                    ),  # only calculate demographics for living patients
                )
            )
        )

        # limit stats to ukrdc
        if limit_to_ukrdc:
            patient_query.where(PatientRecord.sendingextract == "UKRDC")

        # limit number of records returned (for benchmarking)
        if limit_query_length:
            patients = next(
                pd.read_sql(
                    patient_query, self.session.bind, chunksize=limit_query_length
                )
            )

        else:
            patients = pd.read_sql(patient_query, self.session.bind)

        if include_tracing:
            # look to see to find data that might exclude patients from statistics
            # TODO: I still think there is more nuance than this. What if a patient has
            # been discharged or moved abroad or any other reason that they might appear
            # but not have their death recorded.
            exclude_patients = (
                select(PatientRecord.ukrdcid)
                .join(Patient, Patient.pid == PatientRecord.pid)  # type:ignore
                .where(
                    and_(
                        # PatientRecord.sendingfacility == "TRACING",
                        PatientRecord.ukrdcid.in_(
                            patients[pd.isna(patients.deathtime)].ukrdcid
                        ),
                        Patient.death_time < self.date,
                    )
                )
            )

            exclude_patients_list = pd.read_sql(exclude_patients, self.session.bind)

            # filter out patients in the exclusion list
            patients = patients[~patients.ukrdcid.isin(exclude_patients_list.ukrdcid)]

        # map primary renal diagnosis
        patients["PRD"] = patients["diagnosiscode"].replace(PRD_CODE_MAP)

        return patients

    def _calculate_gender(self) -> DoubleLabelled3d:
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        gender = calculate_base_patient_histogram_3D(
            self._patient_cohort, "gender", GENDER_GROUP_MAP
        )

        return DoubleLabelled3d(
            metadata=Basic3dMetadata(
                title="PRD by Gender",
                summary="Breakdown of patient primary renal diagnosis separated by gender",
                description=demographic_descriptions["GENDER_DESCRIPTION"],
                axis_titles=AxisLabel3d(
                    x="Gender", y="Primary Renal Diagnosis", z="No. of Patients"
                ),
            ),
            data=DoubleLabelled3dData(
                x=gender.gender_mapped.tolist(),
                y=gender.PRD.tolist(),
                z=gender.Count.tolist(),
            ),
        )

    def _calculate_age(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # add column with ages and calculate histogram
        self._patient_cohort["age"] = self._patient_cohort["birthtime"][
            pd.isna(self._patient_cohort.deathtime)
        ].apply(lambda dob: age_from_dob(self.date, dob))

        age = calculate_base_patient_histogram_3D(self._patient_cohort, "age")

        return DoubleLabelled3d(
            metadata=Basic3dMetadata(
                title="Age Distribution",
                summary="Distribution of patient ages",
                description=demographic_descriptions["AGE_DESCRIPTION"],
                axis_titles=AxisLabel3d(x="Gender", y="Primary Renal Diagnosis", z=""),
            ),
            data=DoubleLabelled3dData(
                x=age.age.tolist(),
                y=age.PRD.tolist(),
                z=age.Count.tolist(),
            ),
        )

    def _calculate_ethnic_group_code(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        ethnic_group_code = calculate_base_patient_histogram_3D(
            self._patient_cohort, "ethnicgroupcode", ETHNIC_GROUP_MAP
        )

        return DoubleLabelled3d(
            metadata=Basic3dMetadata(
                title="Ethnic Group",
                summary="Breakdown of patient ethnic group codes",
                description=demographic_descriptions["ETHNIC_GROUP_DESCRIPTION"],
                axis_titles=AxisLabel3d(x="Ethnicity", y="No. of Patients"),
            ),
            data=DoubleLabelled3dData(
                x=ethnic_group_code.ethnicgroupcode_mapped.tolist(),
                y=ethnic_group_code.PRD.tolist(),
                z=ethnic_group_code.Count.tolist(),
            ),
        )

    def extract_patient_cohort(
        self,
        include_tracing: Optional[bool] = False,
        limit_to_ukrdc: Optional[bool] = True,
        limit_query_length: Optional[int] = None,
    ):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        include_tracing switch allows patient records created by nhs tracing to be searched
        for DoD.
        """
        self._patient_cohort = self._extract_base_patient_cohort(
            include_tracing=include_tracing,
            limit_to_ukrdc=limit_to_ukrdc,
            limit_query_length=limit_query_length,
        )

    def extract_stats(
        self,
        include_tracing: Optional[bool] = False,
        limit_to_ukrdc: Optional[bool] = True,
        limit_query_length: Optional[int] = None,
    ) -> DemographicsStats:
        """Extract all stats for the demographics module

        Returns:
            DemographicsStats: Demographics statistics object
        """
        # If we don't already have a patient cohort, extract one
        if self._patient_cohort is None:
            self.extract_patient_cohort(
                include_tracing=include_tracing,
                limit_to_ukrdc=limit_to_ukrdc,
                limit_query_length=limit_query_length,
            )

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        pop_size = len(self._patient_cohort[["ukrdcid"]].drop_duplicates())

        # Build output object
        return DemographicsStats(
            metadata=DemographicsMetadata(population=pop_size),
            gender=self._calculate_gender(),
            ethnic_group=self._calculate_ethnic_group_code(),
            age=self._calculate_age(),
        )
