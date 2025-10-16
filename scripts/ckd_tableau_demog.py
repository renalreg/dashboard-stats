"""
This script attempts to replicate the krt demographics extract with a different
(more experimental) CKD calculator being used to produce a cohort of patients 
prior to going on rrt.

Note: As of 19/09/25 some bizarre socket error appears if you use connection
manager. Not sure exactly what is going on here but the current work around is
to use a url passed in an .env file and set up a manual ssh tunnel 
"""


import os
import argparse
import pandas as pd
import datetime as dt

from dotenv import dotenv_values
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rr_connection_manager import PostgresConnection

from ukrdc_stats.calculators.demographics import DemographicStatsCalculator, GENDER_GROUP_MAP
from ukrdc_stats.utils import map_codes, lookup_codes, check_headcounts, short_names, facility_names, region_map
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator
from ukrdc_stats.exceptions import NoCohortError


# Get arguments from command line
parser = argparse.ArgumentParser(description='Extract CKD demographics data')
parser.add_argument('--year-start', type=int, default=2024, help='Starting year for extraction (default: 2024)')
parser.add_argument('--quarter-start', type=int, default=3, help='Starting quarter (1-4) for extraction (default: 3)')
parser.add_argument('--no-of-quarters', type=int, default=4, help='Number of quarters to extract (default: 4)')
parser.add_argument('--output-dir', type=str, default='.do_not_commit', help='Output directory for CSV file (default: .do_not_commit)')
args = parser.parse_args()



# Configuration
YEAR_START = args.year_start
QUARTER_START = args.quarter_start
NO_OF_QUARTERS = args.no_of_quarters
OUTPUT_DIR = Path(args.output_dir)
OUTPUT_FILE = "ckd_demog"
SERVER =  "ukrdc_live"
os.makedirs(OUTPUT_DIR, exist_ok=True)

env_file = dotenv_values(".env")
UKRDC_URL = env_file.get("ukrdc_url")

OUTPUT_FILE = f"{OUTPUT_FILE}_{SERVER}_{YEAR_START}.csv"

# unified list even if centres are not sending careplanning
# TODO: RAQ01 headcount still not quite right
FACILITIES = [
    "RAJ",
    "RAQ01",
    "RCSLB",
    "RH8",
    "RHW01",
#    "RJZ", Kings
    "RK7CC",
    "RL403", 
    "RNJ00",
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
    # This fill missing ethnicities with missing (as distinct to coded as unknown) 
    ethnicity["variable"] = ethnicity["ethnic_group_code"].map(ethnic_group_map).fillna("Missing")
    ethnicity.drop(columns = ["ethnic_group_code"], inplace=True)
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
        "99RCSLB":"99RCSLB",
        "RM574" : "RW3RM", # Birmingham
        "RW3RM":"RW3RM",
        "RJ122" : "RJ122" # Evelina 
    }

    paed_mask = cohort["adultpaed"] == "Paediatric"
    cohort.loc[paed_mask, "centre_code"] = cohort.loc[
        paed_mask, "centre_code"
    ].map(PAED_MAP).fillna("Other")
    

    paed_mask = cohort["adultpaed"] == "Paediatric"
    cohort.loc[paed_mask, "satellite_code"] = cohort.loc[
        paed_mask, "satellite_code"
    ].map(PAED_MAP).fillna("Other")

    # TODO: Same mapping in reverse?

    return cohort

# create a session to connect to the database
if UKRDC_URL:
    ukrdc_session = sessionmaker(create_engine(UKRDC_URL))()
else:
    ukrdc_conn = PostgresConnection(app = SERVER, tunnel = True, via_app = True)
    ukrdc_sessionmaker = ukrdc_conn.session_maker()
    ukrdc_session = ukrdc_sessionmaker()


# loop through the facilities calculating the stats for each of the facilities
# defined at the beginning of the file 
cohorts = []
#region_map = map_codes("RR1", "URTS_region", ukrdc_session)
#facility_names = lookup_codes("RR1+", "description", ukrdc_session)
print("Extracting cohort for facility: ")
for facility in FACILITIES:
    print(facility)
    for q_offset in range(QUARTER_START - 1, QUARTER_START + NO_OF_QUARTERS - 1):
        current_quarter = (q_offset % 4) + 1
        current_year = YEAR_START + q_offset // 4
        try:
            facility_cohort = calculate_ckd_demog(facility, current_year, current_quarter, ukrdc_session)
        except NoCohortError:
            continue
        
        # check basic headcounts for consistancy
        try:
            check_headcounts(facility_cohort)
        except Warning as e:
            print(e)
            continue

        facility_cohort["quarter"] = current_quarter
        facility_cohort["year"] = current_year
        #facility_cohort["region"] = region_map.get(facility, "not in mapping")
        cohorts.append(facility_cohort)


# Export data to csv file
output_order = [
    "variable",
    "centre",
    "adultpaed",
    "dialtplt",
    "country",
    "variable2",
    "centre_code",
    "satellite_code",
    "satellite",
    "year",
    "quarter",
    "region",
    "value"
]

combined_cohort = pd.concat(cohorts)
print("\nWriting to file...")
# Filter any empty rows (can remove small numbers here too)
combined_cohort = combined_cohort[combined_cohort["value"] > 0]
combined_cohort = remap_paed_centres(combined_cohort)
#combined_cohort["satellite"] = combined_cohort["satellite_code"].map(facility_names)    
#combined_cohort["centre"] = combined_cohort["centre_code"].map(facility_names)
combined_cohort["country"] = "England"

combined_cohort["centre"] = combined_cohort["centre_code"].map(short_names)
combined_cohort["region"] = combined_cohort["centre_code"].map(region_map)
combined_cohort["satellite"] = combined_cohort["satellite_code"].map(facility_names)


if not combined_cohort.empty:
    combined_cohort.to_csv(
        os.path.join(OUTPUT_DIR, OUTPUT_FILE), 
        index=False,
        columns=output_order
    )
else:
    raise ValueError("No data extracted")

ukrdc_session.close()