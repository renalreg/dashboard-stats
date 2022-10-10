import datetime as dt
from typing import Optional
import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from ukrdc_sqla.ukrdc import Patient, PatientRecord

from pydantic import BaseModel
from ukrdc_stats.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError

from ukrdc_stats.utils import age_from_dob


from .models.generic_2d import (
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
    AxisLabels2d,
)


class DemographicsMetadata(BaseModel):
    population: Optional[int] = None


class DemographicsStats(BaseModel):
    gender: Labelled2d
    birth_country: Labelled2d
    primary_language: Labelled2d
    ethnic_group_code: Labelled2d
    age: Labelled2d
    metadata: DemographicsMetadata


def _calculate_base_patient_histogram(cohort: pd.DataFrame, group: str) -> pd.DataFrame:
    """Extract a histogram of the patient cohort, grouped by the given column

    Args:
        cohort (pd.DataFrame): Patient cohort
        group (str): Column to group by

    Raises:
        NoCohortError: If the patient cohort is empty

    Returns:
        pd.DataFrame: Histogram dataframe of the patient cohort
    """
    return cohort[["pid", group]].drop_duplicates().groupby([group]).count()


class DemographicsCalculator(AbstractFacilityStatsCalculator):
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
            select(Patient)  # type:ignore
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
        if not self._patient_cohort:
            raise NoCohortError("No patient cohort has been extracted")

        gender = _calculate_base_patient_histogram(self._patient_cohort, "gender")

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Gender Distribution",
                coding_standard_x="NHS_DATA_DICTIONARY",
                axis_titles=AxisLabels2d(x="Gender", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=list(gender.index), y=[item[0] for item in gender.values]
            ),
        )

    def _calculate_birth_country(self):
        if not self._patient_cohort:
            raise NoCohortError("No patient cohort has been extracted")

        birth_country = _calculate_base_patient_histogram(
            self._patient_cohort, "countryofbirth"
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Country of birth",
                coding_standard_x="NHS_DATA_DICTIONARY",
                axis_titles=AxisLabels2d(x="Country", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=list(birth_country.index),
                y=[item[0] for item in birth_country.values],
            ),
        )

    def _calculate_primary_language(self):
        if not self._patient_cohort:
            raise NoCohortError("No patient cohort has been extracted")

        primary_language = _calculate_base_patient_histogram(
            self._patient_cohort, "primarylanguagecode"
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Primary language",
                coding_standard_x="NHS_DATA_DICTIONARY",
                axis_titles=AxisLabels2d(x="Language", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=list(primary_language.index),
                y=[item[0] for item in primary_language.values],
            ),
        )

    def _calculate_ethnic_group_code(self):
        if not self._patient_cohort:
            raise NoCohortError("No patient cohort has been extracted")

        ethnic_group_code = _calculate_base_patient_histogram(
            self._patient_cohort, "ethnicgroupcode"
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Ethnic Group",
                coding_standard_x="NHS_DATA_DICTIONARY",
                axis_titles=AxisLabels2d(x="Ethnicity", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=list(ethnic_group_code.index),
                y=[item[0] for item in ethnic_group_code.values],
            ),
        )

    def _calculate_age(self):
        if not self._patient_cohort:
            raise NoCohortError("No patient cohort has been extracted")

        # add column with ages and calculate histogram
        self._patient_cohort["age"] = self._patient_cohort["birthtime"].apply(
            lambda dob: age_from_dob(self.date, dob)
        )

        age = _calculate_base_patient_histogram(self._patient_cohort, "age")

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Age Distribution",
                axis_titles=AxisLabels2d(x="Age", y="No. of Patients"),
            ),
            data=Labelled2dData(x=list(age.index), y=[item[0] for item in age.values]),
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
        if not self._patient_cohort:
            self.extract_patient_cohort()

        if not self._patient_cohort:
            raise NoCohortError("No patient cohort has been extracted")

        # Crunch the numbers and make dataframes to produce "histograms" to display idividual bits of data
        pop_size = len(self._patient_cohort[["pid"]].drop_duplicates())

        # Build output object
        return DemographicsStats(
            metadata=DemographicsMetadata(population=pop_size),
            gender=self._calculate_gender(),
            birth_country=self._calculate_birth_country(),
            primary_language=self._calculate_primary_language(),
            ethnic_group_code=self._calculate_ethnic_group_code(),
            age=self._calculate_age(),
        )
