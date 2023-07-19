"""
Abstract base classes for the ukrdc_stats package
"""

from abc import ABC, abstractmethod
from typing import Optional

import redis
import pyarrow as pa
import pandas as pd
from sqlalchemy.orm import Session
from ukrdc_stats.exceptions import NoCohortError

from ..models.base import JSONModel


class AbstractFacilityStatsCalculator(ABC):
    """
    Abstract base class for facility stats calculators.

    We only enforce a couple of minor requirements:
    - The class must have a constructor that takes a database session and a facility code
    - The class must have an `extract_patient_cohort` method that assigns a pandas dataframe to the `_patient_cohort` attribute
    - The class must have a `calculate_stats` method that returns calculated stats as a pydantic model
    """

    def __init__(self, session: Session, redis_cache: redis.Redis, facility: str):
        # Set up the database session
        self.session: Session = session
        
        # Connection to redis cache
        self.redis_cache: redis.Redis = redis_cache
        
        self.facility: Optional[str] = facility
        # Create a pandas dataframe to store the results
        self._patient_cohort: Optional[pd.DataFrame] = None

        # Create key for cache 
        self.cache_key: Optional[str] = None

    def check_cache(self, key: str) -> Optional[pd.DataFrame]:
        if self.redis_cache.exists(key):
            # Retrieve serialized DataFrame from Redis cache
            serialized_data = self.redis_cache.get(key)
            self._patient_cohort = pd.read_json(serialized_data.decode())
            print("patient cohort restored from cache")

    def cache_cohort(self, key: str):
        """The philosophy here is the key should be a unique combination of information 
            which represents the parameters the dashboard stats has been run with in this case date 
            and unit. This may cause problems down the line if the data was to change. For example
            you could imagine a unit correcting their data but the same stats appear on the dashboard 
            because the calculator is looking at a cache which is 12 months old. Maybe this will require
            a clear cache button or something more clever on the UI.

            In theory pandas has a to_dict method but pyarrow should be a) more efficent and memory frendly
            pyarrow.feather might be an option worth looking into b) it's not encrypted but the data isn't human readable     
        """
        if self._patient_cohort is not None:
            self.redis_cache.set(key, self._patient_cohort.to_json())

    @abstractmethod
    def extract_patient_cohort(self) -> None:
        """
        Extract the patient cohort from the database, and assign it to self._patient_cohort

        The self.patient_cohort variable should contain everything nessary to calculate the 
        denominators for the statistics produced by the calculator. Usually this means the 
        identifies of a bunch of patients based on the XYZ conditions. 
        """

    @abstractmethod
    def extract_stats(self) -> JSONModel:
        """
        Extract all stats from the patient cohort and return them in a Pydantic object

        Returns:
            JSONModel: Pydantic object containing all related stats
        """
        





