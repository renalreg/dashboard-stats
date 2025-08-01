"""
This script attempts to replicate the krt demographics extract with a different
(more experimental) KRT calculator.
"""

import datetime as dt
import os
import pandas as pd

from sqlalchemy.orm import Session
from rr_connection_manager import PostgresConnection
from scripts.extract_ckd import prevalence_point
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator

# Configuration
YEAR = 2024
OUTPUT_DIR = ".do_not_commit"
SERVER =  "ukrdc_live"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FACILITIES = [
    "RCSLB"    
]


def calculate_tableau_demog(cohort:pd.DataFrame, facility:str, start:dt.datetime, stop:dt.datetime, ukrdc_session:Session):
    """
    Function to aggregate demographics data in a tableau digestible way
    """

    # initialise demographics and create report
    demographics_calculator = DemographicStatsCalculator(
        session=ukrdc_session,
        facility=facility,
        end_date=stop,
        start_date=start
    )
    _, demographics_report = demographics_calculator.produce_report(
        output_columns=["gender", "age", "ethnic_group_code"]
    )
    demographics_report = demographics_report.to_pandas()
   
    # Introduce adultpediatric flag
    demographics_report["adultpaed"] = demographics_report["age"].astype(int) > 18 
    demographics_report["adultpaed"] = demographics_report["adultpaed"].map({True: "Adult", False: "Pediatric"})

    # Aggregate gender
    gender = pd.merge(cohort, demographics_report[["ukrdcid","gender", "adultpaed"]], on="ukrdcid")
    gender["variable"] = gender["gender"].map(GENDER_GROUP_MAP)
    gender.drop(columns = ["gender"], inplace=True)
    gender.drop_duplicates(inplace=True)
    gender = gender.groupby(["satellite_code", "centre", "incidprev", "variable", "adultpaed"]).size().reset_index(name="value")

    # Aggregate age 
    age = pd.merge(cohort, demographics_report[["ukrdcid","age", "adultpaed"]], on="ukrdcid")
    age["value"] = age["age"].astype(int)
    bins = [0, 18, 25, 35, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 999]
    labels = ['<18', '18-24', '25-34', '35-44', '45-49', '50-54', '55-59', 
              '60-64', '65-69', '70-74', '75-79', '80-84', '85-89', '90+']
    age["variable"] = pd.cut(age["value"], bins=bins, labels=labels, right=False)
    age.drop_duplicates(inplace=True)
    age = age.groupby(["satellite_code", "centre", "incidprev", "variable", "adultpaed"]).size().reset_index(name="value")

    # Aggregate ethnicity
    ethnic_group_map = map_codes("NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", session)
    ethnicity = pd.merge(cohort, demographics_report[["ukrdcid","ethnic_group_code", "adultpaed"]], on="ukrdcid")
    ethnicity["variable"] = ethnicity["ethnic_group_code"].map(ethnic_group_map)
    ethnicity.drop(columns = ["ethnic_group_code"], inplace=True )
    ethnicity.drop_duplicates(inplace=True)
    ethnicity = ethnicity.groupby(["satellite_code", "centre", "incidprev", "variable", "adultpaed"]).size().reset_index(name="value")

    # Combine dataframes together
    gender["variable2"] = "Gender"
    ethnicity["variable2"] = "Ethnicity"
    age["variable2"] = "Age"

    return pd.concat([gender, ethnicity, age])



def calculate_ckd_demog(facility:str, prevalence_point:dt.datetime, ukrdc_session:Session):
    """
    Function to aggregate data in a tableau digestible way
    """
    calculator = PrevalentCKDCalculator(
        session=ukrdc_session, 
        facility=facility, 
        prevalence_point=prevalence_point,
    )
    calculator.extract_patient_cohort()
    _, ckd_cohort = calculator.produce_report(
        output_columns=["ukrdcid", "admitreasoncode", "healthcarefacilitydesc","sendingfacility"]
    )
    ckd_cohort.drop_duplicates(inplace=True)
    
    return calculate_tableau_demog(ckd_cohort, facility, prevalence_point, prevalence_point, ukrdc_session)




ukrdc_conn = PostgresConnection(app = SERVER, tunnel = True, via_app = True)
ukrdc_sessionmaker = ukrdc_conn.session_maker()
prevalence_point = dt.datetime(YEAR, 12, 31, 23, 59, 59)
with ukrdc_sessionmaker() as ukrdc_session:
    for facility in FACILITIES:
        calculate_ckd_demog(facility, prevalence_point, ukrdc_session)