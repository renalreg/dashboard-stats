"""
This module contains the calculators associated with chronic kidney disease. 
That is patients which are identified as having kidney disease but are not in recipt KRT.
"""
import redis

import datetime as dt
import pandas as pd
from typing import Optional, List

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_, select
from ukrdc_stats.exceptions import NoCohortError
from ukrdc_sqla.ukrdc import (
    PatientRecord,
    Patient,
    Treatment,
    LabOrder,
    ResultItem
)

from ukrdc_stats.models.base import JSONModel
from ukrdc_stats.utils import dob_cutoff_from_age


class ChronicKidneyDiseaseBase(AbstractFacilityStatsCalculator):
    """This will calculate the base level 

    Args:
        AbstractFacilityStatsCalculator (_type_): _description_
    """
    def __init__(
        self, 
        session: Session, 
        redis_cache: redis.Redis, 
        facility: str, 
        date: Optional[dt.datetime] = None
    ):
        """Initialises the PatientDemographicStats class and immediately runs the relevant query

        Args:
            session (SQLAlchemy session): Connection to database to calculate statistic from.
            facility (str): Facility to calculate the
            date (datetime, optional): Date to calculate at. Defaults to today.
        """
        super().__init__(session, redis_cache, facility)

        # Set the date to calculate at, defaulting to today
        self.date: dt.datetime = date or dt.datetime.today()


    def extract_stats(self) -> JSONModel:
        
        # if that doesn't work try extracting one
        if self._patient_cohort is None:
            self.extract_patient_cohort(self.facility, self.date)

        # if we still have no cohort raise an error 
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

    
    def _extract_base_patient_cohort(self, facility) -> pd.DataFrame:
        
        patient_query = (
            select(
                PatientRecord.ukrdcid,
                PatientRecord.sendingfacility,
                Patient.birth_time,
                Patient.death_time, 
                Treatment.admit_reason_code,
                ResultItem.serviceidcode,
                LabOrder.orderitemcode,
                ResultItem.enteredon,
                ResultItem.resultvalue,
                ResultItem.resultvalueunits

            ).join(PatientRecord, Patient.pid == PatientRecord.pid)
            .join(Treatment, Treatment.pid == PatientRecord.pid, isouter=True)
            .join(LabOrder, LabOrder.pid == Patient.pid, isouter = True)
            .join(ResultItem, LabOrder.id == ResultItem.order_id, isouter=True)
            .where(
                and_(
                    PatientRecord.sendingfacility == facility,
                    PatientRecord.sendingextract == "UKRDC",
                    or_(
                        Patient.death_time.is_(None), Patient.death_time > self.date
                    ),
                    # TODO: Think this should be an or condition with a CKD codelist  
                    Treatment.admit_reason_code.is_(None),
                    or_(
                        ResultItem.serviceidcode == "QBLAP",
                        ResultItem.serviceidcode == "QBLAR",
                        ResultItem.serviceidcode == "QBLA1"
                    ),
                    ResultItem.enteredon < self.date
                )
            )
        )

        return pd.read_sql(patient_query, self.session.bind).drop_duplicates()
    
    def extract_patient_cohort(self, facility, date) -> None:
        cache_key = f"{facility}:{date.month}:{date.year}"
        # restore patient cohort from cache
        if date.day == 1:
            self.check_cache(key = cache_key)

        # extract and cache dataset for calculation of stats the patient cohort should 
        if self._patient_cohort is None:
            self._patient_cohort = self._extract_base_patient_cohort(self.facility)
            self.cache_cohort(key = cache_key)
        else:
            # serialisation process converts datetimes to Unix times...this needs reverting for data restored from the cache
            self._patient_cohort["birthtime"] = pd.to_datetime(self._patient_cohort["birthtime"], unit='ms')
            self._patient_cohort["deathtime"] = pd.to_datetime(self._patient_cohort["deathtime"], unit='ms')
            self._patient_cohort["enteredon"] = pd.to_datetime(self._patient_cohort["enteredon"], unit='ms')



    def recent_egfr_result(self):
        # count total number of patients in cohort 
        numerator = len(self._patient_cohort.ukrdcid.drop_duplicates())
        
        # count total number of patients with a recent test
        denominator = len(
            self._patient_cohort[
                self._patient_cohort.enteredon > dob_cutoff_from_age(self.date, 1)].ukrdcid.drop_duplicates())
        
        return numerator / denominator

class ChronicKidneyDiseaseScaleCompare(ChronicKidneyDiseaseBase):
    def __init__(
        self, 
        session: Session, 
        redis_cache: redis.Redis,
        facility: str, 
        comparison_facilities: List[str], 
        date: Optional[dt.datetime] = None,
    ):
        if date.day != 1:
            print("warning: snapped to the first of month")
        
        self.date = dt.datetime(date.year, date.month,1)
        super().__init__(session, redis_cache, facility)
        
        self.comparison_facilities = comparison_facilities

        # Set up the database session
        self.session: Session = session
        
        # Connection to redis cache
        self.redis_cache: redis.Redis = redis_cache
        
        # Set up list 

        # Create a pandas dataframe to store the results
        self._patient_cohort: Optional[pd.DataFrame] = None

        # Create key for cache 
        self.cache_key: Optional[str] = None

    #def extract_patient_cohort(self):
    #    for facility in self.comparison_facilities:
                  

#class ChronicKidneyDiseaseLongditudinal()  

