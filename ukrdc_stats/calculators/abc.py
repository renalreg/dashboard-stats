"""
Abstract base classes for the ukrdc_stats package
"""

from abc import ABC, abstractmethod
from typing import Optional, List

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select

from ukrdc_stats.models.base import JSONModel
from ukrdc_stats.models.generic_2d import BaseTable
from ukrdc_stats.exceptions import NoCohortError

from ukrdc_sqla.ukrdc import PatientNumber


class AbstractFacilityStatsCalculator(ABC):
    """
    Abstract base class for facility stats calculators.

    We only enforce a couple of minor requirements:
    - The class must have a constructor that takes a database session and a facility code
    - The class must have an `extract_patient_cohort` method that assigns a pandas dataframe to the `_patient_cohort` attribute
    - The class must have a `calculate_stats` method that returns calculated stats as a pydantic model
    """

    def __init__(
        self, session: Session, facility: str, redis_cache_session: Session = None
    ):
        # Set up the database session
        self.session: Session = session

        self.redis_cache_session: Session = redis_cache_session

        # Store the facility code
        self.facility: str = facility

        # Create a pandas dataframe to store the results
        self._patient_cohort: Optional[pd.DataFrame] = None

    def produce_report(
        self,
        input_filters: list[str],
        output_columns: List[str],
        include_ni: bool = False,
    ) -> BaseTable:
        """
        Produce report containing the patients from a cohort displayed in the
        as aggregated stats. As UI users can't query patients on the pid they
        should probably be returned as a list of mrns.
        """

        if self._patient_cohort is None:
            raise NoCohortError

        dataframe_filter = "(" + ")&(".join(input_filters) + ")"
        patient_record_filtered = self._patient_cohort.query(dataframe_filter)

        # Create a table of the specified records
        report = (
            patient_record_filtered[output_columns]
            .drop_duplicates()
            .reset_index(drop=True)
        )

        if include_ni:
            patient_numbers = pd.DataFrame(
                self.session.execute(
                    select(PatientNumber.pid, PatientNumber.patientid).where(
                        PatientNumber.organization == "NHS",
                        PatientNumber.pid.in_(report.pid.drop_duplicates()),
                    )
                ),
            ).rename(columns={"patientid": "nhsno"})

            report = pd.merge(report, patient_numbers, on="pid", how="left")
            report["nhsno"] = report["nhsno"].fillna("Unknown")

        population = len(report.pid.drop_duplicates())

        return population, BaseTable(
            headers=report.columns.tolist(),
            rows=[row.tolist() for _, row in report.iterrows()],
        )

    def store(self):
        pass

    def retrieve(self):
        pass

    @abstractmethod
    def extract_patient_cohort(self) -> None:
        """
        Extract the patient cohort from the database, and assign it to self._patient_cohort
        """

    @abstractmethod
    def extract_stats(self) -> JSONModel:
        """
        Extract all stats from the patient cohort and return them in a Pydantic object

        Returns:
            JSONModel: Pydantic object containing all related stats
        """
