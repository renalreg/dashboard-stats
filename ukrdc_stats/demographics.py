import datetime as dt
from typing import Optional, List
import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from ukrdc_sqla.ukrdc import Patient, Treatment

from pydantic import BaseModel

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


class DemographicsCalculator:
    """Calculates the demographics information based on the personal infomation listed in the patient table"""

    def __init__(
        self,
        session: Session,
        facility: str,
        date: dt.datetime = dt.datetime.today(),
        modality_list=None,
    ):
        """Initialises the PatientDemographicStats class and immediately runs the relevant query

        Args:
            session (SQLAlchemy session): Connection to database to calculate statistic from.
            facility (str): Facility to calculate the
            date (datetime, optional): Date to calculate at. Defaults to today.
        """

        self.session: Session = session
        self.facility: str = facility
        self.date: dt.datetime = date
        self.modality_list = None

        if modality_list:
            self.modality_list = modality_list
        else:
            self.modality_list = None

        # Immediately run the patient cohort query, so it's ready for re-use
        self.patient_cohort: pd.DataFrame = self._extract_patient_cohort()

    def _extract_patient_cohort(self) -> pd.DataFrame:
        """
        Extracts the patient cohort from the database into a pandas dataframe
        """

        # select all patients with modalities that haven't finished
        patient_query = (
            select(Patient)
            .join(Treatment)
            .where(
                and_(
                    Treatment.pid == Patient.pid,
                    Treatment.health_care_facility_code == self.facility,
                    (Treatment.from_time < self.date),
                    (Treatment.to_time.is_(None)) | (Treatment.to_time >= self.date),
                    (Patient.death_time >= self.date) | (Patient.death_time.is_(None)),
                )
            )
        )

        return pd.read_sql(patient_query, self.session.bind)

    def _make_patient_histogram(self, group: str) -> pd.DataFrame:

        return (
            self.patient_cohort[["pid", group]]
            .drop_duplicates()
            .groupby([group])
            .count()
        )

    def _make_age_histogram(self, age_bins: List[int]):

        # make column with ages of patients
        self.patient_cohort["age"] = self.patient_cohort["birthtime"].apply(
            lambda dob: age_from_dob(self.date, dob)
        )

        # bin cohort on age
        binned_data = self.patient_cohort[["pid", "age"]].drop_duplicates()
        binned_data["bins"] = pd.cut(binned_data.age, age_bins)
        histogram = binned_data.groupby(["bins"])["bins"].count().values

        return histogram

    def extract_stats(self):
        """
        Extract demographic statistics from the patient cohort dataframe
        """

        # Crunch the numbers and make dataframes to produce "histograms" to display idividual bits of data
        pop_size = len(self.patient_cohort[["pid"]].drop_duplicates())

        gender = self._make_patient_histogram("gender")
        birth_country = self._make_patient_histogram("countryofbirth")
        primary_language = self._make_patient_histogram("primarylanguagecode")
        ethnic_group_code = self._make_patient_histogram("ethnicgroupcode")

        age_bins = [18, 28, 38, 48, 58, 68, 78, 120]
        age = self._make_age_histogram(age_bins)
        age_labels = [f"{age_bins[i]}-{age_bins[i+1]-1}" for i in range(len(age) - 1)]
        age_labels.append("78+")

        # Build output object
        return DemographicsStats(
            metadata=DemographicsMetadata(population=pop_size),
            gender=Labelled2d(
                metadata=Labelled2dMetadata(
                    title="Gender Distribution",
                    coding_standard_x="NHS_DATA_DICTIONARY",
                    axis_titles=AxisLabels2d(x="Gender", y="No. of Patients"),
                ),
                data=Labelled2dData(
                    x=list(gender.index), y=[item[0] for item in gender.values]
                ),
            ),
            birth_country=Labelled2d(
                metadata=Labelled2dMetadata(
                    title="Country of birth",
                    coding_standard_x="NHS_DATA_DICTIONARY",
                    axis_titles=AxisLabels2d(x="Country", y="No. of Patients"),
                ),
                data=Labelled2dData(
                    x=list(birth_country.index),
                    y=[item[0] for item in birth_country.values],
                ),
            ),
            primary_language=Labelled2d(
                metadata=Labelled2dMetadata(
                    title="Primary language",
                    coding_standard_x="NHS_DATA_DICTIONARY",
                    axis_titles=AxisLabels2d(x="Language", y="No. of Patients"),
                ),
                data=Labelled2dData(
                    x=list(primary_language.index),
                    y=[item[0] for item in primary_language.values],
                ),
            ),
            ethnic_group_code=Labelled2d(
                metadata=Labelled2dMetadata(
                    title="Ethnic Group",
                    coding_standard_x="NHS_DATA_DICTIONARY",
                    axis_titles=AxisLabels2d(x="Ethnicity", y="No. of Patients"),
                ),
                data=Labelled2dData(
                    x=list(ethnic_group_code.index),
                    y=[item[0] for item in ethnic_group_code.values],
                ),
            ),
            age=Labelled2d(
                metadata=Labelled2dMetadata(
                    title="Age Distribution",
                    axis_titles=AxisLabels2d(x="Age", y="No. of Patients"),
                ),
                data=Labelled2dData(x=age_labels, y=list(age)),
            ),
        )
