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

        # Set the cache_key if date is first of the month any process using 
        # data caching should only call the calcualator on(for) the first of the month
        # this is to avoid caching too much data 
        if self.date.day == 1:
            self.cache_key = f"{self.facility}:{self.date.month}:{self.date.year}"

    def extract_stats(self) -> JSONModel:
        
        # if we have no patient cohort we check the cache
        if self._patient_cohort is None and self.date.day == 1:
            self.check_cache(self.cache_key)

        
        # if that doesn't work try extracting one
        if self._patient_cohort is None:
            self.extract_patient_cohort()
            print("patient cohort extracted from ukrdc")
        else:
            # serialisation process converts datetimes to Unix times...this needs reverting
            self._patient_cohort["birthtime"] = pd.to_datetime(self._patient_cohort["birthtime"], unit='ms')
            self._patient_cohort["deathtime"] = pd.to_datetime(self._patient_cohort["deathtime"], unit='ms')
            self._patient_cohort["enteredon"] = pd.to_datetime(self._patient_cohort["enteredon"], unit='ms')

        # if we still have no cohort raise an error 
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

    
    def _extract_base_patient_cohort(self, facility) -> pd.DataFrame:

        patient_query = (
            select(
                PatientRecord.ukrdcid,
                PatientRecord.sending
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
    
    def extract_patient_cohort(self) -> None:
        # extract and cache dataset for calculation of stats the patient cohort should 
        self._patient_cohort = self._extract_base_patient_cohort(self.facility)
        self.cache_cohort(self.cache_key)


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
        
        # Set up the database session
        self.session: Session = session
        
        # Connection to redis cache
        self.redis_cache: redis.Redis = redis_cache
        
        # Set up list 

        # Create a pandas dataframe to store the results
        self._patient_cohort: Optional[pd.DataFrame] = None

        # Create key for cache 
        self.cache_key: Optional[str] = None
        

#class ChronicKidneyDiseaseLongditudinal()  

