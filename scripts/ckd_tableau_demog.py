"""
This script attempts to replicate the krt demographics extract with a different
(more experimental) CKD calculator being used to produce a cohort of patients 
prior to going on rrt.

Note: As of 19/09/25 some bizarre socket error appears if you use connection
manager. Not sure exactly what is going on here but the current work around is
to use a url passed in an .env file and set up a manual ssh tunnel 
"""

import datetime as dt
import os
import pandas as pd

from dotenv import dotenv_values
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator, GENDER_GROUP_MAP
from ukrdc_stats.utils import map_codes, lookup_codes
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator
from ukrdc_stats.exceptions import NoCohortError


# Configuration
YEAR = 2023
#OUTPUT_DIR = Path("Q:") / Path("UKRDC") / Path("UKRDC_Dashboard")
OUTPUT_DIR = Path(".do_not_commit")
OUTPUT_FILE = "ckd_demog"
SERVER =  "ukrdc_live"
os.makedirs(OUTPUT_DIR, exist_ok=True)

env_file = dotenv_values(".env")
UKRDC_URL = env_file.get("ukrdc_url")

OUTPUT_FILE = f"{OUTPUT_FILE}_{SERVER}_{YEAR}.csv"

# dump of facilities in staging removed_xml_archive
FACILITIES = [
    "RAJ",
    "RNJ00",
    "RAQ01",
    #"RBD01",
    #"RBT20",
    "RCSLB",
    #"RDEE4",
    #"RFBAK",
    "RH8",
    #"RHW01",
    #"RJ121",
    #"RJ122",
    #"RJE01",
    "RJZ",
    "RK7CC",
    "RNJ00",
    #"RKB01",
    #"RL403",
    #"RLZ01",
    #"RM574",
    #"RNX02",
    #"RRE01",
    #"RRK02"
]

def calculate_tableau_demog(
    cohort:pd.DataFrame, 
    facility:str, 
    start:dt.datetime, 
    stop:dt.datetime, 
    group_by_columns: list,
    ukrdc_session:Session):
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
   
    demographics_report["adultpaed"] = demographics_report["age"].astype(int) > 18 
    demographics_report["adultpaed"] = demographics_report["adultpaed"].map({True: "Adult", False: "Paediatric"})

    # Total head count 
    total =  pd.merge(cohort, demographics_report[["ukrdcid","adultpaed"]], on="ukrdcid")
    total["variable"] = total["dialtplt"]
    total.drop_duplicates(inplace=True)
    total = total.groupby(group_by_columns).size().reset_index(name="value")

    # Remove Paeds from the demogs
    demographics_report = demographics_report[demographics_report["adultpaed"] == "Adult"]

    # Aggregate gender
    gender = pd.merge(cohort, demographics_report[["ukrdcid","gender", "adultpaed"]], on="ukrdcid")
    gender["variable"] = gender["gender"].map(GENDER_GROUP_MAP)
    gender.drop(columns = ["gender"], inplace=True)
    gender.drop_duplicates(inplace=True)
    gender = gender.groupby(group_by_columns).size().reset_index(name="value")

    # Aggregate age 
    age = pd.merge(cohort, demographics_report[["ukrdcid","age", "adultpaed"]], on="ukrdcid")
    age["value"] = age["age"].astype(int)
    bins = [18, 25, 35, 45, 55, 65, 75, 85, 150]
    labels = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", ">=85"]
    age["variable"] = pd.cut(age["value"], bins=bins, labels=labels, right=False)
    age.drop_duplicates(inplace=True)
    age = age.groupby(group_by_columns).size().reset_index(name="value")

    # Aggregate ethnicity
    ethnic_group_map = map_codes("NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", ukrdc_session)
    ethnicity = pd.merge(cohort, demographics_report[["ukrdcid","ethnic_group_code", "adultpaed"]], on="ukrdcid")
    ethnicity["variable"] = ethnicity["ethnic_group_code"].map(ethnic_group_map)
    ethnicity.drop(columns = ["ethnic_group_code"], inplace=True )
    ethnicity.drop_duplicates(inplace=True)
    ethnicity = ethnicity.groupby(group_by_columns).size().reset_index(name="value")
 
    # Combine dataframes together
    gender["variable2"] = "Sex"
    ethnicity["variable2"] = "Ethnicity"
    age["variable2"] = "Age"
    total["variable2"] = "Clinic Type"

    return pd.concat([total, gender, ethnicity, age])


def calculate_ckd_demog(facility:str, year:int, quarter:int, ukrdc_session:Session):
    """
    Function to aggregate data in a tableau digestible way
    """

    if quarter < 4:
        prevalence_point = dt.datetime(year, 3*quarter + 1, 1, 0, 0, 0) - dt.timedelta(days=1)
    else:
        prevalence_point = dt.datetime(year, 12, 31)

    # Initiate the calculator to produce a granular ckd cohort
    calculator = PrevalentCKDCalculator(
        session=ukrdc_session, 
        facility=facility, 
        prevalence_point=prevalence_point,
    )
    calculator.extract_patient_cohort()
    _, ckd_cohort = calculator.produce_report(
        output_columns=[
            "ukrdcid", 
            "admitreasoncode",
            "healthcarefacilitycode", 
            "healthcarefacilitydesc",
            "sendingfacility",
            "resultvalue_labegfr",
            "calculated_egfr"
        ]
    )
    ckd_cohort = ckd_cohort.to_pandas().drop_duplicates()
    # Apply egfr filter to ckd patients to remove any patients with egfr
    # greater than CKD threshold. 
    # TODO: should this be part of the cohort definition?
    ckd_cohort = ckd_cohort[
        (ckd_cohort["calculated_egfr"].notna() & (ckd_cohort["calculated_egfr"].astype(float) <= 15)) | 
        (ckd_cohort["resultvalue_labegfr"].notna() & (ckd_cohort["resultvalue_labegfr"].astype(float) <= 15)) |
        (ckd_cohort["calculated_egfr"].isna() & ckd_cohort["resultvalue_labegfr"].isna())
    ]


    # Relabel columns and relabel data in dialplt
    ckd_cohort.rename(
        columns={
            "sendingfacility": "centre_code",  
            "healthcarefacilitycode": "satellite_code",
            "healthcarefacilitydesc": "satellite", 
            "admitreasoncode":"dialtplt",
        }, 
        inplace=True
    )
    ckd_cohort["dialtplt"] = ckd_cohort["dialtplt"].replace({"902": "AKC", "903": "NEPH"})
    
    if not ckd_cohort["dialtplt"].isna().empty:
        # TODO: follow up why missing modalities (shouldn't be possible)
        #raise ValueError("Extract has produced patients with missing treatment modalities")
        ckd_cohort.loc[
            ckd_cohort["dialtplt"].isna(),
            "dialtplt"
        ] = "NA"

    ckd_cohort.loc[
        ~ckd_cohort["dialtplt"].isin(["AKC", "NEPH", "NA"]),
        "dialtplt"
    ] = "Other"

    # Columns which will remain in the aggregated data
    group_by_columns = [
        "satellite_code", 
        "satellite", 
        "centre_code", 
        "variable", 
        "adultpaed", 
        "dialtplt"
    ]

    return calculate_tableau_demog(ckd_cohort, facility, prevalence_point, prevalence_point, group_by_columns, ukrdc_session)

def remap_paed_centres(cohort:pd.DataFrame):
    """Currently this is under discussion. For now we will only map patients
    under 18 who are sent by main centers known to share a feed with a Paed
    centre.
    """

    PAED_MAP = {
        "RCSLB" : "99RCSLB", # Nottingham
        "RM574" : "RW3RM", # Birmingham
        "RJ122" : "RJ122" # Evelina 
    }

    paed_mask = cohort["adultpaed"] == "Paediatric"
    cohort.loc[paed_mask, "centre_code"] = cohort.loc[
        paed_mask, "centre_code"
    ].map(PAED_MAP).fillna("Other")
    
    return cohort

if UKRDC_URL:
    ukrdc_session = sessionmaker(create_engine(UKRDC_URL))()
else:
    ukrdc_conn = PostgresConnection(app = SERVER, tunnel = True, via_app = True)
    ukrdc_sessionmaker = ukrdc_conn.session_maker()
    ukrdc_session = ukrdc_sessionmaker()

cohorts = []
region_map = map_codes("RR1", "URTS_region", ukrdc_session)
facility_names = lookup_codes("RR1+", "description", ukrdc_session)
print("Extracting cohort for facility: ")
for facility in FACILITIES:
    #print(f"{facility}", end = ",")
    print(facility)
    for quarter in range(1,5):
        # Append various placeholder columns for variables not being swept
        try:
            facility_cohort = calculate_ckd_demog(facility, YEAR, quarter, ukrdc_session)
        except NoCohortError:
            continue

        facility_cohort["quarter"] = quarter

        facility_cohort["region"] = region_map.get(facility, "not in mapping")
        facility_cohort["centre"] = facility_names.get(facility, "not in mapping")
        cohorts.append(facility_cohort)


# Export data to csv file
output_order = [
    "variable",
    "centre",
    "adultpaed",
    "dialtplt",
    "country",
    "variable2",
    "measure",
    "centre_code",
    "satellite_code",
    "satellite",
    "year",
    "option",
    "incidprev",
    "quarter",
    "region",
    "value"
]

combined_cohort = pd.concat(cohorts)
print("\nWriting to file...")
# Filter any empty rows (can remove small numbers here too)
combined_cohort = combined_cohort[combined_cohort["value"] > 0]
combined_cohort["satellite"] = combined_cohort["satellite_code"].map(facility_names)    
combined_cohort = remap_paed_centres(combined_cohort)
combined_cohort["year"] = YEAR
combined_cohort["option"] = "Number"
combined_cohort["country"] = "England"
combined_cohort["measure"] = "Demography"
combined_cohort["incidprev"] = "Prevalent"

if not combined_cohort.empty:
    combined_cohort.to_csv(
        os.path.join(OUTPUT_DIR, OUTPUT_FILE), 
        index=False,
        columns=output_order
    )
else:
    raise ValueError("No data extracted")

ukrdc_session.close()