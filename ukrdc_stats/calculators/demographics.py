"""
Patient cohort demographics stats calculator
"""

import datetime as dt
from typing import Optional, Dict
import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from ukrdc_sqla.ukrdc import Patient, PatientRecord

from pydantic import BaseModel
from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError

from ukrdc_stats.utils import age_from_dob

from ukrdc_stats.code_groupings import ETHNIC_GROUP_MAP, GENDER_GROUP_MAP


from ..models.generic_2d import (
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
    AxisLabels2d,
)


class DemographicsMetadata(BaseModel):
    population: Optional[int] = None


class DemographicsStats(BaseModel):
    gender: Labelled2d
    ethnic_group: Labelled2d
    age: Labelled2d
    metadata: DemographicsMetadata


def _calculate_base_patient_histogram(
    cohort: pd.DataFrame, group: str, code_map: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """Extract a histogram of the patient cohort, grouped by the given column

    Args:
        cohort (pd.DataFrame): Patient cohort
        group (str): Column to group by

    Raises:
        NoCohortError: If the patient cohort is empty

    Returns:
        pd.DataFrame: Histogram dataframe of the patient cohort
    """

    if code_map:
        mapped_column = f"{group}_mapped"
        cohort[mapped_column] = cohort[group].map(code_map)

        histogram = (
            cohort[["ukrdcid", mapped_column]]
            .drop_duplicates()
            .groupby([mapped_column])
            .count()
            .reset_index()
        )

    else:
        histogram = (
            cohort[["ukrdcid", group]]
            .drop_duplicates()
            .groupby([group])
            .count()
            .reset_index()
        )

    return histogram.rename(columns={"ukrdcid": "Count"})


class DemographicStatsCalculator(AbstractFacilityStatsCalculator):
    """Calculates the demographics information based on the personal infomation listed in the patient table"""

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

    def _extract_base_patient_cohort(self) -> pd.DataFrame:
        """
        Extracts the patient cohort from the database into a pandas dataframe
        """

        # TODO: Add ability to filter on modality

        # select all patients with modalities that haven't finished
        patient_query = (
            select(
                PatientRecord.ukrdcid,
                Patient.gender,
                Patient.ethnic_group_code,
                Patient.birth_time,
            )  # type:ignore
            .join(PatientRecord, Patient.pid == PatientRecord.pid)  # type:ignore
            .where(
                and_(
                    PatientRecord.sendingextract == "UKRDC",
                    PatientRecord.sendingfacility == self.facility,
                )
            )
        )

        return pd.read_sql(patient_query, self.session.bind)

    def _calculate_gender(self) -> Labelled2d:
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        gender = _calculate_base_patient_histogram(
            self._patient_cohort, "gender", GENDER_GROUP_MAP
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Gender Distribution",
                summary="",
                description="",
                axis_titles=AxisLabels2d(x="Gender", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=gender.gender_mapped.tolist(), y=gender.Count.tolist()
            ),
        )

    def _calculate_ethnic_group_code(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        ethnic_group_code = _calculate_base_patient_histogram(
            self._patient_cohort, "ethnicgroupcode", ETHNIC_GROUP_MAP
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Ethnic Group",
                summary="",
                description="",
                axis_titles=AxisLabels2d(x="Ethnicity", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=ethnic_group_code.ethnicgroupcode_mapped.tolist(),
                y=ethnic_group_code.Count.tolist(),
            ),
        )

    def _calculate_age(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # add column with ages and calculate histogram
        self._patient_cohort["age"] = self._patient_cohort["birthtime"].apply(
            lambda dob: age_from_dob(self.date, dob)
        )

        age = _calculate_base_patient_histogram(self._patient_cohort, "age")

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Age Distribution",
                summary="",
                description="",
                axis_titles=AxisLabels2d(x="Age", y="No. of Patients"),
            ),
            data=Labelled2dData(x=age.age.tolist(), y=age.Count.tolist()),
        )

    def extract_patient_cohort(self):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        """
        self._patient_cohort = self._extract_base_patient_cohort()

    def extract_stats(self) -> DemographicsStats:
        """Extract all stats for the demographics module

        Returns:
            DemographicsStats: Demographics statistics object
        """
        # If we don't already have a patient cohort, extract one
        if self._patient_cohort is None:
            self.extract_patient_cohort()

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        pop_size = len(self._patient_cohort[["ukrdcid"]].drop_duplicates())

        # Build output object
        return DemographicsStats(
            metadata=DemographicsMetadata(population=pop_size),
            ethnic_group=self._calculate_ethnic_group_code(),
            gender=self._calculate_gender(),
            age=self._calculate_age(),
        )
