"""
Abstract base classes for the ukrdc_stats package
"""

from abc import ABC, abstractmethod
from typing import Optional, List

import pandas as pd
import datetime as dt
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ukrdc_sqla.ukrdc import PatientRecord, Patient

from ukrdc_stats.models.base import JSONModel
from ukrdc_stats.models.generic_2d import BaseTable
from ukrdc_stats.exceptions import NoCohortError

from ukrdc_sqla.ukrdc import PatientNumber
from ukrdc_stats.utils import GENDER_GROUP_MAP, map_codes, AGE_BINS


class AbstractFacilityStatsCalculator(ABC):
    """
    Abstract base class for facility stats calculators.

    We only enforce a couple of minor requirements:
    - The class must have a constructor that takes a database session and a facility code
    - The class must have an `extract_patient_cohort` method that assigns a pandas dataframe to the `_patient_cohort` attribute
    - The class must have a `calculate_stats` method that returns calculated stats as a pydantic model
    """

    def __init__(
        self,
        session: Session,
        facility: str,
        date: Optional[dt.datetime] = None,
    ):
        # Set up the database session
        self.session: Session = session

        # Store the facility code
        self.facility: str = facility

        # Create a pandas dataframe to store the results
        self._patient_cohort: Optional[pd.DataFrame] = None

        self.date = date or dt.datetime.now()

    def produce_report(
        self,
        output_columns: List[str],
        input_filters: list[str] = None,
        include_ni: bool = False,
    ) -> BaseTable:
        """
        Produce report containing the patients from a cohort displayed in the
        as aggregated stats. As UI users can't query patients on the pid they
        should probably be returned as a list of mrns.
        """
        if self._patient_cohort is None:
            self.extract_patient_cohort()

        if self._patient_cohort is None:
            raise NoCohortError

        if "ukrdcid" not in output_columns:
            output_columns.append("ukrdcid")

        if input_filters:
            dataframe_filter = "(" + ")&(".join(input_filters) + ")"
            patient_record_filtered = self._patient_cohort.query(dataframe_filter)
        else:
            patient_record_filtered = self._patient_cohort

        population = len(patient_record_filtered.ukrdcid.drop_duplicates())

        report = (
            patient_record_filtered[output_columns]
            .drop_duplicates()
            .reset_index(drop=True)
        )

        if include_ni:
            patient_numbers = pd.DataFrame(
                self.session.execute(
                    select(PatientRecord.ukrdcid, PatientNumber.patientid)
                    .join(PatientRecord, PatientNumber.pid == PatientRecord.pid)
                    .where(
                        PatientNumber.organization == "NHS",
                        PatientRecord.ukrdcid.in_(report.ukrdcid.drop_duplicates()),
                    )
                ),
            ).rename(columns={"patientid": "nhsno"})

            report = pd.merge(report, patient_numbers, on="ukrdcid", how="left")
            report["nhsno"] = report["nhsno"].fillna("Unknown")
            report = report.drop_duplicates()

        return population, BaseTable(
            headers=report.columns.tolist(),
            rows=[row.tolist() for _, row in report.iterrows()],
        )

    # Constrain extract patient cohort with
    def extract_patient_cohort(self, **kwargs):
        self._extract_patient_cohort(**kwargs)
        self._validate_patient_cohort(self._patient_cohort)

    @abstractmethod
    def _extract_patient_cohort(self) -> None:
        """
        Extract the patient cohort from the database, and assign it to self._patient_cohort
        """

    def _validate_patient_cohort(self, dataframe: pd.DataFrame):
        """
        There are certain constraint
        """
        if self._patient_cohort is None:
            raise ValueError(
                "Patient cohort extractor has failed to produce the _patient_cohort dataframe"
            )

        required_columns = {"pid", "ukrdcid", "sendingfacility"}
        missing_columns = required_columns - set(dataframe.columns)
        if missing_columns:
            raise ValueError(f"Missing columns in patient cohort: {missing_columns}")

    # All calculators should contain a method to extract aggregated stats as a
    # pydantic object for api of the UI to use
    @abstractmethod
    def extract_stats(self) -> JSONModel:
        """
        Extract all stats from the patient cohort and return them in a Pydantic object

        Returns:
            JSONModel: Pydantic object containing all related stats
        """

    def _query_demographics(self, patient_list):
        """Generalized query to return the demographic information

        Args:
            patient_list (_type_): _description_

        Returns:
            _type_: _description_
        """

        query_demog = (
            select(
                PatientRecord.pid,
                Patient.gender,
                Patient.ethnicgroupcode,
                func.date(Patient.birthtime).label("dob"),
                func.date_part("year", func.age(self.date, Patient.birthtime)).label(
                    "age"
                ),
                func.coalesce(Patient.deathtime > self.date, True).label("is_alive"),
            )
            .join(PatientRecord, Patient.pid == PatientRecord.pid)
            .where(
                PatientRecord.pid.in_(patient_list),
            )
        )

        return pd.DataFrame(self.session.execute(query_demog)).drop_duplicates()

    def _relabel_demographics(self, demographics_raw):
        # Map age to fixed bins
        demographics_raw["age"] = demographics_raw["age"].astype(int)
        bins = AGE_BINS["bins"]
        labels = AGE_BINS["labels"]
        for i in range(len(labels)):
            demographics_raw.loc[
                (bins[i + 1] > demographics_raw["age"])
                & (bins[i] <= demographics_raw["age"]),
                "agerange",
            ] = labels[i]

        demographics_raw.loc[~demographics_raw["is_alive"], "agerange"] = "Deceased"
        demographics_raw.loc[demographics_raw["agerange"] == "Deceased", "age"] = None

        # Map gender to stats groups
        demographics_raw["gender"] = (
            demographics_raw["gender"]
            .map(GENDER_GROUP_MAP, None)
            .fillna("Unknown/Uncoded")
        )

        # Map ethnicity to stats groups
        ethnic_group_map = map_codes(
            "NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", self.session
        )
        demographics_raw["ethnicity"] = (
            demographics_raw["ethnicgroupcode"]
            .map(ethnic_group_map, None)
            .fillna("Unknown/Uncoded")
        )

        return demographics_raw

    def append_demographics(self):
        if self._patient_cohort is None:
            raise ValueError(
                "Please extract cohort before appending demographic information"
            )

        # get demographic attributes from database

        # break up large queries into chunks to avoid PostgreSQL stack overflow
        batch_size = 1000
        demographics = []
        for i in range(0, len(self._patient_cohort), batch_size):
            batch = self._patient_cohort.iloc[i : i + batch_size]
            demographics.append(self._query_demographics(batch.pid))

        demographics = self._relabel_demographics(pd.concat(demographics))

        # merge back into patient cohort and remove duplicated columns
        self._patient_cohort = self._patient_cohort.merge(
            demographics, how="left", on="pid", suffixes=("", "_extra")
        )
        self._patient_cohort = self._patient_cohort.loc[
            :, ~self._patient_cohort.columns.str.endswith("_extra")
        ]

    # For future implementation postcode lookup against external api
    def append_deprivation_index(self):
        pass

    # For future implementation to cache cohorts to improve retrieval speed
    def store(self):
        pass

    def retrieve(self):
        pass
