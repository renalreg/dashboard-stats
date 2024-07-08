"""
Patient cohort demographics stats calculator
"""

import datetime as dt
from typing import Dict, Optional
import warnings
from pydantic import Field

import pandas as pd
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import Patient, PatientRecord

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError
from ukrdc_stats.utils import age_from_dob, map_codes

from ..descriptions import demographic_descriptions
from ..models.base import JSONModel
from ..models.generic_2d import (
    AxisLabels2d,
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
)

# NHS digital gender map
GENDER_GROUP_MAP = {"1": "Male", "2": "Female", "9": "Indeterminate", "X": "Unknown"}


class DemographicsMetadata(JSONModel):
    population: Optional[int] = Field(
        None, description="Population demographics are calculated from"
    )


class DemographicsStats(JSONModel):
    gender: Labelled2d = Field(..., description="Gender demographic stats")
    ethnic_group: Labelled2d = Field(
        ...,
        description="Ethnicity Histogram based on the 5 ethnicity groupings used in the annual report",
    )
    age: Labelled2d = Field(..., description="Age statistics of living patients")
    metadata: DemographicsMetadata = Field(
        ..., description="Metadata describing demographic stats"
    )


def _mapped_key(key: str) -> str:
    """Tiny convenience function to return a common mapped column name

    Args:
        key (str): Column to map

    Returns:
        str: Mapped column name
    """
    return f"{key}_mapped"


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
        mapped_column = _mapped_key(group)
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


def _mapped_if_exists(df: pd.DataFrame, column: str) -> pd.Series:
    """
    Convenience function to return the mapped column if it exists,
    otherwise return the original column

    Args:
        df (pd.DataFrame): Input dataframe
        column (str): Column to return

    Returns:
        pd.Series: Mapped column if it exists, otherwise the original column
    """
    mapped_column: str = _mapped_key(column)
    if mapped_column in df.columns:
        return df[mapped_column]
    else:
        warnings.warn(
            f"Column {mapped_column} does not exist in dataframe, returning {column} instead"
        )
        return df[column]


class DemographicStatsCalculator(AbstractFacilityStatsCalculator):
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

        # TODO: Add ability to filter on modality

        # select all patients who have a patientrecord sent from the facility
        patient_query = (
            select(
                PatientRecord.ukrdcid,
                Patient.gender,
                Patient.ethnic_group_code,
                Patient.birth_time,
                Patient.death_time,
            )  # type:ignore
            .join(PatientRecord, Patient.pid == PatientRecord.pid)  # type:ignore
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
            patient_query = patient_query.where(PatientRecord.sendingextract == "UKRDC")

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

        return patients.drop_duplicates()

    def _calculate_gender(self) -> Labelled2d:
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        gender = _calculate_base_patient_histogram(
            self._patient_cohort, "gender", GENDER_GROUP_MAP
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Gender Distribution",
                summary="Breakdown of patient gender identity codes",
                description=demographic_descriptions["GENDER_DESCRIPTION"],
                axis_titles=AxisLabels2d(x="Gender", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=_mapped_if_exists(gender, "gender").tolist(), y=gender.Count.tolist()
            ),
        )

    def _calculate_ethnic_group_code(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        #        print(ethnic_groups)
        ethnic_group_map = map_codes(
            "NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", self.session
        )

        ethnic_group_code = _calculate_base_patient_histogram(
            self._patient_cohort, "ethnicgroupcode", ethnic_group_map
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Ethnic Group",
                summary="Breakdown of patient ethnic group codes",
                description=demographic_descriptions["ETHNIC_GROUP_DESCRIPTION"],
                axis_titles=AxisLabels2d(x="Ethnicity", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=_mapped_if_exists(ethnic_group_code, "ethnicgroupcode").tolist(),
                y=ethnic_group_code.Count.tolist(),
            ),
        )

    def _calculate_age(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # add column with ages and calculate histogram
        self._patient_cohort["age"] = self._patient_cohort["birthtime"][
            pd.isna(self._patient_cohort.deathtime)
        ].apply(lambda dob: age_from_dob(self.date, dob))

        age = _calculate_base_patient_histogram(self._patient_cohort, "age")

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Age Distribution",
                summary="Distribution of patient ages",
                description=demographic_descriptions["AGE_DESCRIPTION"],
                axis_titles=AxisLabels2d(x="Age", y="No. of Patients"),
            ),
            data=Labelled2dData(x=age.age.tolist(), y=age.Count.tolist()),
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
            ethnic_group=self._calculate_ethnic_group_code(),
            gender=self._calculate_gender(),
            age=self._calculate_age(),
        )
