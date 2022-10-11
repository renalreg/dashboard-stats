"""
Abstract base classes for the ukrdc_stats package
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from pydantic import BaseModel
from sqlalchemy.orm import Session


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

    @abstractmethod
    def extract_patient_cohort(self) -> None:
        """
        Extract the patient cohort from the database, and assign it to self._patient_cohort
        """

    @abstractmethod
    def extract_stats(self) -> BaseModel:
        """
        Extract all stats from the patient cohort and return them in a Pydantic object

        Returns:
            BaseModel: Pydantic object containing all related stats
        """
