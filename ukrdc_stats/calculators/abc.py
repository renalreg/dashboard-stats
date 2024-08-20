"""
Abstract base classes for the ukrdc_stats package
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

import pandas as pd
from sqlalchemy.orm import Session

from  ukrdc_stats.models.base import JSONModel
from ukrdc_stats.models.generic_2d import BaseTable, RowData
from ukrdc_stats.exceptions import NoCohortError

class AbstractFacilityStatsCalculator(ABC):
    """
    Abstract base class for facility stats calculators.

    We only enforce a couple of minor requirements:
    - The class must have a constructor that takes a database session and a facility code
    - The class must have an `extract_patient_cohort` method that assigns a pandas dataframe to the `_patient_cohort` attribute
    - The class must have a `calculate_stats` method that returns calculated stats as a pydantic model
    """
 
    def __init__(self, session: Session, facility: str):
        # Set up the database session
        self.session: Session = session
        # Store the facility code
        self.facility: str = facility

        # Create a pandas dataframe to store the results
        self._patient_cohort: Optional[pd.DataFrame] = None
    

    def produce_report(self, input_filters:list[str], output_columns:List[str]) -> BaseTable:
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
        report = patient_record_filtered[output_columns].drop_duplicates().reset_index(drop=True)    

        return BaseTable(
            headers=output_columns,
            #rows = [row.copy().tolist() for _, row in report.T.iterrows()]
            rows = [row.copy().tolist() for _, row in report.iterrows()]
        )


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
