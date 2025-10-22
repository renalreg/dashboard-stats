"""
This is a template to base Tableau vis extracts from the UKRDC
The basic cohort is always made the same, and best checked before any joins or manipulations

Depending on the data to be visualised it then adds
1. Demographics (in almost all examples) using the UKRDC patient table
2. Renal Transplant care planning using the xmlarchive
3. Dialysis access for ICHD patients using the UKRDC dialysissessions table
4. Supplements clinic type using the xmlarchive

"""

import os
import warnings
import argparse
import datetime as dt
import pandas as pd

from dotenv import dotenv_values
from pathlib import Path

from rr_connection_manager import PostgresConnection

from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session, sessionmaker

from ukrdc_stats.calculators.krt import KRTStatsCalculator
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator, GENDER_GROUP_MAP
from ukrdc_stats.calculators.ckd import get_archive_session
from ukrdc_stats.utils import map_codes, lookup_codes, check_headcounts, age_from_dob
from ukrdc_stats.exceptions import NoCohortError

from ukrdc_sqla.xmlarchive import Assessment, Patient
from ukrdc_sqla.ukrdc import Patient, PatientNumber, PatientRecord, DialysisSession

### Get arguments from command line
parser = argparse.ArgumentParser(description='Extract CKD demographics data')
parser.add_argument('--year-start', type=int, default=2024, help='Starting year for extraction (default: 2024)')
parser.add_argument('--quarter-start', type=int, default=3, help='Starting quarter (1-4) for extraction (default: 3)')
parser.add_argument('--no-of-quarters', type=int, default=4, help='Number of quarters to extract (default: 4)')
parser.add_argument('--output-dir', type=str, default='.do_not_commit', help='Output directory for CSV file (default: .do_not_commit)')
args = parser.parse_args()

### Configuration
YEAR_START = args.year_start
QUARTER_START = args.quarter_start
NO_OF_QUARTERS = args.no_of_quarters
OUTPUT_DIR = Path(args.output_dir)

OUTPUT_FILE = "krt_demog"
SERVER =  "ukrdc_live"
# SERVER =  "ukrdc_staging"
OUTPUT_FILE = f"{OUTPUT_FILE}_{SERVER}_{YEAR_START}.csv"
os.makedirs(OUTPUT_DIR, exist_ok=True)

env_file = dotenv_values(".env")
UKRDC_URL = env_file.get("ukrdc_url")

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

# FACILITIES = ["RFBAK"]

### Start of Cohort generating and then aggregating functions
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

# James M 21-Oct-2025 Aggregate the incident and prevalent numbers before other manipulations for later comparison
    check_cohort = combined_report.groupby(["satellite_code", "dialtplt", "incidprev"], dropna=False).size().reset_index(name="value")
    check_cohort["Start"] = start

    # what about home hd?
    combined_report["dialtplt"] = combined_report["dialtplt"].map({"PD":"PD","TX":"Transplant","HD":"HD"}).fillna("Missing")
    combined_report.drop(columns = ["admitreasoncode", "admitreasoncodestd", "fromtime", "totime"], inplace=True)

# JM 22-Oct-25 Simpler demographics df on everyone from sendingfacility to reduce risk of missing data
    query = (
    select(
        PatientRecord.ukrdcid,
        Patient.gender,
        Patient.birthtime,
        Patient.ethnic_group_code
    )
    .join(Patient, Patient.pid == PatientRecord.pid)
    .where(and_(PatientRecord.sendingfacility == facility), PatientRecord.sendingextract == "UKRDC")
)

    demographics_report = pd.DataFrame(ukrdc_session.execute(query))
    demographics_report["birthtime"] = pd.to_datetime(demographics_report["birthtime"])
    demographics_report['age'] = (start - demographics_report['birthtime']).dt.days / 365.25
    demographics_report.drop(columns = ["birthtime"], inplace=True)

    # Introduce adultpediatric flag (age threshold)
    demographics_report["adultpaed"] = demographics_report["age"] > 18 
    demographics_report["adultpaed"] = demographics_report["adultpaed"].map({True: "Adult", False: "Paediatric"}).fillna("Adult")

    # Total headcount
    total = pd.merge(combined_report, demographics_report[["ukrdcid","adultpaed"]], on="ukrdcid", how="left")
    total["variable"] = total["dialtplt"]

    # Limit rest of demogs to adults only 
    demographics_report = demographics_report[demographics_report["adultpaed"] == "Adult"]
    
    if len(demographics_report) == 0:
        raise NoCohortError(f"No Adults in facility {facility}")

    # link data on gender
    gender = pd.merge(combined_report, demographics_report[["ukrdcid","gender", "adultpaed"]], on="ukrdcid", how="left")
    gender["variable"] = gender["gender"].map(GENDER_GROUP_MAP).fillna("Missing")
    gender.drop(columns = ["gender"], inplace=True)

    # link data on age label into fixed bins
    # 21-Oct-25 James M.  Need to make a 'missing' category otherwise does not add up (having first ensured removed people really < 18 we make NAs = zero)
    age = pd.merge(combined_report, demographics_report[["ukrdcid","age", "adultpaed"]], on="ukrdcid", how="left")
    age["age"] = age["age"].replace(pd.NA, '0')
#    age["age"] = age["age"].astype('int64')
    bins = [0, 18, 35, 55, 75, 150]
    labels = ["Missing","18-34", "35-54", "55-74", ">=75"]
    for i in range(len(labels)):
        age.loc[(bins[i+1] > age["age"]) & (bins[i] <= age["age"]), "variable"] = labels[i]
    age.drop(columns = ["age"], inplace=True)

    # Link data on ethnicity
    ethnic_group_map = map_codes("NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", ukrdc_session)
    ethnicity = pd.merge(combined_report, demographics_report[["ukrdcid","ethnic_group_code", "adultpaed"]], on="ukrdcid", how="left")
    ethnicity["variable"] = ethnicity["ethnic_group_code"].map(ethnic_group_map).fillna("Missing")
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

    return demog_combined, check_cohort

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

### End of Cohort generating and then aggregating functions 

### Main routine
# Connect to database
if UKRDC_URL:
    ukrdc_session = sessionmaker(create_engine(UKRDC_URL))()
else:
    ukrdc_conn = PostgresConnection(app = SERVER, tunnel = True, via_app = True)
    ukrdc_sessionmaker = ukrdc_conn.session_maker()
    ukrdc_session = ukrdc_sessionmaker()

single_quarter_cohorts = []
headcount_cohorts = []

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
            tableau_demog, check_cohort = calculate_tableau_demog(
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
        headcount_cohorts.append(check_cohort)

    # remap Paeds and add centre names and regions
    combined_cohort = pd.concat(single_quarter_cohorts)
    combined_cohort = remap_paed_centres(combined_cohort)
    region_map = map_codes("RR1", "URTS_region", ukrdc_session)
    facility_names = lookup_codes("RR1+", "description", ukrdc_session)
    combined_cohort["centre"] = combined_cohort["centre_code"].map(facility_names)
    combined_cohort["region"] = combined_cohort["centre_code"].map(region_map)
    combined_cohort["satellite"] = combined_cohort["satellite_code"].map(facility_names)

    headcount_cohort = pd.concat(headcount_cohorts)

# Finally some hard coded bits
combined_cohort["country"] = "England"

# Filter any empty rows (can remove small numbers here too)
combined_cohort = combined_cohort[combined_cohort["value"] > 0]

print("\nWriting to file...")
# Export headcount checks to csv file
headcount_cohort.to_csv(os.path.join(OUTPUT_DIR, f"krt_demog_{SERVER}_{YEAR_START}_headcounts.csv"))

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