"""
Example of how to extend the dashboard stats functionality using pandas to
produce an extract which is compatible with the tableau visualisations on the
UKKidney website here:
https://www.ukkidney.org/audit-research/data-portals

Hosted here:
https://public.tableau.com/app/profile/ukkidney/viz/KRTlandingpage/Landingpage

In this script the following is calculated:
total head count for adult and paeds
age breakdown for adults krt patients
sex breakdown for adults krt patients
ethnicity breakdown for adults krt patients
gender breakdown for adults krt patients
vascular access for hd patients
"""
# James M 08-10-25 I have removed DOESNOTCONTAIN, PDC etc from the mapping for vascular access to precipitate it filling with NA as these are not valid entries
#                   I have commented out line 217 as we need to count the NA (and not convert to NTL)
#                   Line 239 I have added 'dropna=False' to the group function to force count of NA

import os
import argparse
import warnings
import pandas as pd
import datetime as dt

from dotenv import dotenv_values
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.krt import KRTStatsCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator, GENDER_GROUP_MAP
from ukrdc_stats.utils import map_codes, lookup_codes, check_headcounts
from ukrdc_stats.exceptions import NoCohortError
from ukrdc_sqla.ukrdc import PatientRecord, DialysisSession
from sqlalchemy import select


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

OUTPUT_FILE = "krt_demog"
SERVER =  "ukrdc_live"
os.makedirs(OUTPUT_DIR, exist_ok=True)

env_file = dotenv_values(".env")
UKRDC_URL = env_file.get("ukrdc_url")

OUTPUT_FILE = f"{OUTPUT_FILE}_{SERVER}_{YEAR_START}.csv"

# Note this could be replaced with some sort of lookup when the codes are 
# sorted out also RNJ00 has broken data which will break the extract 
FACILITIES = [
    "RAJ",
    "RAQ01",
    "RCSLB",
    "RH8",
    "RHW01",
#    "RJZ", Kings
    "RK7CC",
    "RL403", 
    "RNJ00"
]

def query_vascular_access(session:Session, patient_list:pd.Series):
    """ Customised version of the _query_vascular_access function which doesn't
    aggregate the results. We may wish to adapt this to get the most recent va
    to a given date.

    Args:
        session (Session): Database session
        patient_list (pd.Series): List of pids defining a cohort.

    Returns:
        pd.DataFrame: _description_
    """
    VASCULAR_MAPPING = {
        "AVF":"AVF/AVG",
        "AVFUO":"AVF/AVG",
        "AVG":"AVF/AVG",
        "TLN":"TL",
        "NLN":"NTL",
        "HER":"AVF/AVG"
    }


    query = (
        select(
            PatientRecord.pid,
            DialysisSession.procedure_time,
            DialysisSession.qhd20
        )
        .join(DialysisSession, DialysisSession.pid == PatientRecord.pid)
        .where(PatientRecord.pid.in_(patient_list))
        .order_by(PatientRecord.pid, DialysisSession.procedure_time)
    )

    vascular_access = pd.DataFrame(session.execute(query))
    if vascular_access.empty:
        vascular_access = pd.DataFrame(columns=["pid", "procedure_time", "qhd20"])

    vascular_access["qhd20"] = vascular_access["qhd20"].map(VASCULAR_MAPPING)
     
    # deduplicate on first value
    vascular_access = vascular_access.sort_values(by="procedure_time").drop_duplicates(subset="pid", keep="first")
    
    return vascular_access.rename(columns={"qhd20":"variable"})

def calculate_tableau_demog(facility:str, start:dt.datetime, stop:dt.datetime, ukrdc_session:Session, aggregated = True):
    """
    Function to aggregate data in a tableau digestible way
    """

    # initialise KRT calculator
    krt_calculator = KRTStatsCalculator(
        session=ukrdc_session, 
        facility=facility, 
        from_time=start, 
        to_time=stop
    )

    # create reports on incident and prevalent patients
    incident_krt_report = (
        krt_calculator.generate_cohort_report(
            cohort="incident"
        ).table.to_pandas()
    )
    incident_krt_report["incidprev"] = "Incident"
     
    prevalent_krt_report = (
        krt_calculator.generate_cohort_report(
            cohort="prevalent"
        ).table.to_pandas()
    )
    prevalent_krt_report["incidprev"] = "Prevalent"
    
    # Mash them together and do some remapping 
    combined_report = pd.concat([incident_krt_report, prevalent_krt_report])
    if len(combined_report) == 0:
        raise NoCohortError("No cohort found for facility skipping: {}".format(facility))

    combined_report.rename(
        columns = {
            "registry_code_type":"dialtplt",
            "healthcarefacilitycode":"satellite_code"
        },
        inplace=True
    )

    # what about home hd?
    combined_report["dialtplt"] = combined_report["dialtplt"].map({"PD":"PD","TX":"Transplant","HD":"HD"})
    combined_report.drop(columns = ["admitreasoncode", "admitreasoncodestd", "fromtime", "totime"], inplace=True)

    # initialise demographics and create report
    demographics_calculator = DemographicStatsCalculator(
        session=ukrdc_session,
        facility=facility,
        end_date=stop,
        start_date=start,
    )
    _, demographics_report = demographics_calculator.produce_report(
        output_columns=["gender", "age", "ethnic_group_code"]
    )
    demographics_report = demographics_report.to_pandas()
   
    # Introduce adultpediatric flag (age threshold)
    demographics_report["adultpaed"] = demographics_report["age"].astype(int) > 18 
    demographics_report["adultpaed"] = demographics_report["adultpaed"].map({True: "Adult", False: "Paediatric"})

    # Total headcount
    total = pd.merge(combined_report, demographics_report[["ukrdcid","adultpaed"]], on="ukrdcid")
    total["variable"] = total["dialtplt"]

    # Limit rest of demogs to adults only 
    demographics_report = demographics_report[demographics_report["adultpaed"] == "Adult"]
    
    if len(demographics_report) == 0:
        raise NoCohortError(f"No Adults in facility {facility}")

    # link data on gender
    gender = pd.merge(combined_report, demographics_report[["ukrdcid","gender", "adultpaed"]], on="ukrdcid")
    gender["variable"] = gender["gender"].map(GENDER_GROUP_MAP)
    gender.drop(columns = ["gender"], inplace=True)

    # link data on age label into fixed bins
    age = pd.merge(combined_report, demographics_report[["ukrdcid","age", "adultpaed"]], on="ukrdcid")
    age["age"] = age["age"].astype(int)
    bins = [18, 35, 55, 75, 150]
    labels = ["18-34", "35-54", "55-74", ">=75"]
    for i in range(len(labels)):
        age.loc[(bins[i+1] > age["age"]) & (bins[i] <= age["age"]), "variable"] = labels[i]
    age.drop(columns = ["age"], inplace=True)

    # Link data on ethnicity
    ethnic_group_map = map_codes("NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", ukrdc_session)
    ethnicity = pd.merge(combined_report, demographics_report[["ukrdcid","ethnic_group_code", "adultpaed"]], on="ukrdcid")
    ethnicity["variable"] = ethnicity["ethnic_group_code"].map(ethnic_group_map)
    ethnicity.drop(columns = ["ethnic_group_code"], inplace=True )

    # Extract first vascular access for adult HD patients
    #hd_patients = combined_report[(combined_report["dialtplt"] == "HD") & ~combined_report.pid.isin(child_pids)]
    hd_patients = total[
        (total["adultpaed"] == "Adult")
        & (total["dialtplt"] == "HD")
    ].drop_duplicates()

    vascular_access = query_vascular_access(ukrdc_session, hd_patients.pid) 
    vascular_access = vascular_access[vascular_access.procedure_time <= stop]
    hd_access = pd.merge(hd_patients, vascular_access, on="pid", how="left")
    hd_access.drop(columns = ["procedure_time"], inplace=True)
#    hd_access.fillna("NTL", inplace=True)

    # label each dataframe with the type of data it is calculating
    gender["variable2"] = "Sex"
    ethnicity["variable2"] = "Ethnicity"
    age["variable2"] = "Age"
    total["variable2"] = "KRT Type"
    hd_access["variable2"] = "Vascular Access"
    demog_combined = pd.concat([total, gender, ethnicity, age, hd_access])
    demog_combined.drop_duplicates(inplace = True)

    # At this point the data should basically be a bunch of labelled ids
    # We can check that they sum to the same value
    n_gender = demog_combined[demog_combined["variable2"]=="Sex"].pid.nunique()
    n_ethnicity = demog_combined[demog_combined["variable2"]=="Ethnicity"].pid.nunique()
    n_age = demog_combined[demog_combined["variable2"]=="Age"].pid.nunique()
    n_krt = demog_combined[demog_combined["variable2"]=="KRT Type"].pid.nunique()

    if n_gender != n_ethnicity or n_gender !=n_age or n_gender !=n_krt:
        warnings.warn("Number of patients does not match across all demographics")


    # debug 
    debug_demog = demog_combined[
        (demog_combined["variable2"] == "Vascular Access")
        & ~demog_combined["pid"].isin(age.pid.to_list())
    ]

    if aggregated:
        demog_combined = demog_combined.groupby(["satellite_code", "incidprev", "variable", "adultpaed", "dialtplt", "variable2"], dropna=False).size().reset_index(name="value")
    

    return demog_combined

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
    ].map(PAED_MAP).fillna("unknown")
    
    return cohort

# Connect to database
if UKRDC_URL:
    ukrdc_session = sessionmaker(create_engine(UKRDC_URL))()
else:
    ukrdc_conn = PostgresConnection(app = SERVER, tunnel = True, via_app = True)
    ukrdc_sessionmaker = ukrdc_conn.session_maker()
    ukrdc_session = ukrdc_sessionmaker()

# conn = PostgresConnection(app="ukrdc_staging", tunnel=True, via_app=True)
# sessionmaker = conn.session_maker()
single_quarter_cohorts = []


for facility in FACILITIES:
    for quarter in range(QUARTER_START-1, QUARTER_START + NO_OF_QUARTERS -1):
        # calculate year, quarter, and dates that bound it 
        current_quarter = (quarter % 4) + 1
        current_year = YEAR_START + quarter // 4    
        quarter_start = dt.datetime(current_year, current_quarter*3-2, 1)
        if current_quarter < 4:
            quarter_end = dt.datetime(current_year, current_quarter*3 +1, 1) - dt.timedelta(days=1)
        else:
            quarter_end = dt.datetime(current_year, 12, 31) 
        
        # Extract data and add additional labels
        try:
            tableau_demog = calculate_tableau_demog(
                facility, 
                quarter_start, 
                quarter_end, 
                ukrdc_session
            )
        except NoCohortError:
            continue

        tableau_demog["quarter"] = current_quarter
        tableau_demog["year"] = current_year
        tableau_demog["centre_code"] = facility
        try:
            check_headcounts(
                tableau_demog[tableau_demog["dialtplt" ]=="HD"],
                [
                    "centre_code",
                    "incidprev", 
                    "variable2"
                ]
            )
        except Warning as e:
            print(e)

        single_quarter_cohorts.append(tableau_demog)
        

    # remap Paeds and add centre names and regions
    combined_cohort = pd.concat(single_quarter_cohorts)
    combined_cohort = remap_paed_centres(combined_cohort)
    region_map = map_codes("RR1", "URTS_region", ukrdc_session)
    facility_names = lookup_codes("RR1+", "description", ukrdc_session)
    combined_cohort["centre"] = combined_cohort["centre_code"].map(facility_names)
    combined_cohort["region"] = combined_cohort["centre_code"].map(region_map)
    combined_cohort["satellite"] = combined_cohort["satellite_code"].map(facility_names)

# Finally some hard coded bits
combined_cohort["country"] = "England"


# Filter any empty rows (can remove small numbers here too)
combined_cohort = combined_cohort[combined_cohort["value"] > 0]

print("\nWriting to file...")

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
    "incidprev",
    "quarter",
    "region",
    "value"
]
if not combined_cohort.empty:
    combined_cohort.to_csv(
        os.path.join(OUTPUT_DIR, OUTPUT_FILE), 
        index=False,
        columns=output_order
    )
else:
    raise ValueError("No data extracted")