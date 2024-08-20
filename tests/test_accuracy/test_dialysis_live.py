"""
Tests/debug helpers designed to be run with a real database connection. We can
also use them for verification against known ukrdc data.
"""

from sqlalchemy.orm import Session 
from ukrdc_stats.calculators.dialysis import DialysisStatsCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator
import datetime as dt
import json

def test_dialysis_base_cohort(ukrdc3_real_db_session:Session):
    if ukrdc3_real_db_session is not None:
        calculator = DialysisStatsCalculator(
            ukrdc3_real_db_session, 
            "RNJ00", 
            from_time=dt.datetime(2021, 12, 31), 
            to_time=dt.datetime(2022, 12, 31)
        )

        dialysis_stats = calculator.extract_stats()
        incident_patients = dialysis_stats.all.incident_krt.data
        all_patients = dialysis_stats.all.all_treatments_krt
        
        filtered = calculator._patient_cohort.copy()
        report = calculator.generate_cohort_report("incident")


def test_demographics_base_cohort(ukrdc3_real_db_session:Session):
    if ukrdc3_real_db_session is not None:
        calculator = DemographicStatsCalculator(
            ukrdc3_real_db_session, 
            "RNJ00", 
            date=dt.datetime(2022, 12, 31)
        )
        demog_stats = calculator.extract_stats()
        age = demog_stats.age.data.dict()
        ethnic_group = demog_stats.ethnic_group.data.dict()
        gender = demog_stats.gender.data.dict()
        population = demog_stats.metadata.population

        formatted_output = demog_stats.dict()
