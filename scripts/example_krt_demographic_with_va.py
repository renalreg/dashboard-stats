import datetime as dt
import os
import pandas as pd

from sqlalchemy.orm import Session
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.krt import KRTStatsCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator, GENDER_GROUP_MAP
from ukrdc_stats.utils import map_codes, lookup_codes
from ukrdc_stats.exceptions import NoCohortError
from ukrdc_sqla.ukrdc import PatientRecord, DialysisSession
from sqlalchemy import select

# Configuration
YEAR = 2024
OUTPUT_DIR = ".do_not_commit"
OUTPUT_FILE = "tableau_krt_demog_va.csv"
SERVER =  "ukrdc_staging"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Note this could be replaced with some sort of lookup when the codes are 
# sorted out
FACILITIES = [
    "RAJ",
    "RAQ01",
    "RBD01",
    "RBT20",
    "RCSLB",
    "RDEE4",
    "RFBAK",
    "RH8",
    "RHW01",
    "RJ121",
    "RJ122",
    "RJE01",
    "RJZ",
    "RK7CC",
    "RKB01",
    "RL403",
    "RLZ01",
    "RM574",
    "RNJ00",
    "RNX02",
    "RRE01",
    "RRK02"
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
    
    query = (
        select(
            PatientRecord.pid,
            DialysisSession.procedure_time,
            DialysisSession.qhd20
        )
        .distinct(PatientRecord.pid)
        .join(DialysisSession, DialysisSession.pid == PatientRecord.pid)
        .where(PatientRecord.pid.in_(patient_list))
        .order_by(PatientRecord.pid, DialysisSession.procedure_time)
    )

    return pd.DataFrame(session.execute(query))

def calculate_tableau_demog(facility:str, start:dt.datetime, stop:dt.datetime, ukrdc_session:Session):
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
    combined_report.rename(
        columns = {
            "registry_code_type":"dialtplt",
            "healthcarefacilitycode":"satellite_code"
        },
        inplace=True
    )

    # drop TX and PD patients 
    combined_report = combined_report[combined_report.dialtplt == "HD"]

    # We get the vascular access in the first recorded dialysis session and
    # drop any results after prevalence point and left join onto cohort
    vascular_access = query_vascular_access(session, combined_report.pid)
    if vascular_access.empty:
        return None
    print(vascular_access.head(5))
    vascular_access = vascular_access[vascular_access.procedure_time <= stop]
    vascular_access.rename(columns={"qhd20":"vascularaccess"}, inplace=True)
    combined_report = pd.merge(combined_report, vascular_access[["pid", "vascularaccess"]], on="pid", how="left")
    combined_report["vascularaccess"] = combined_report["vascularaccess"].fillna("Uncoded")
    combined_report.drop(columns = ["pid", "admitreasoncode", "admitreasoncodestd"], inplace=True)


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
#    demographics_report["adultpaed"] = demographics_report["age"].astype(int) > 18 
#    demographics_report["adultpaed"] = demographics_report["adultpaed"].map({True: "Adult", False: "Paediatric"})
    demographics_report["adultpaed"] = 'Adult'

    # Aggregate gender
    gender = pd.merge(combined_report, demographics_report[["ukrdcid","gender", "adultpaed"]], on="ukrdcid")
    gender["variable"] = gender["gender"].map(GENDER_GROUP_MAP)
    gender.drop(columns = ["gender"], inplace=True)
    gender.drop_duplicates(inplace=True)
    gender = gender.groupby(["satellite_code", "incidprev", "variable", "adultpaed", "dialtplt",  "vascularaccess"]).size().reset_index(name="value")

    # Aggregate age 
    age = pd.merge(combined_report, demographics_report[["ukrdcid","age", "adultpaed"]], on="ukrdcid")
    age["value"] = age["age"].astype(int)
    bins = [18, 25, 35, 45, 55, 65, 75, 85, 150]
    labels = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", ">=85"]
    age["variable"] = pd.cut(age["value"], bins=bins, labels=labels, right=False)
    age.drop_duplicates(inplace=True)
    age = age.groupby(["satellite_code",  "incidprev", "variable", "adultpaed", "dialtplt",  "vascularaccess"]).size().reset_index(name="value")

    # Aggregate ethnicity
    ethnic_group_map = map_codes("NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", session)
    ethnicity = pd.merge(combined_report, demographics_report[["ukrdcid","ethnic_group_code", "adultpaed"]], on="ukrdcid")
    ethnicity["variable"] = ethnicity["ethnic_group_code"].map(ethnic_group_map)
    ethnicity.drop(columns = ["ethnic_group_code"], inplace=True )
    ethnicity.drop_duplicates(inplace=True)
    ethnicity = ethnicity.groupby(["satellite_code", "incidprev", "variable", "adultpaed","dialtplt", "vascularaccess"]).size().reset_index(name="value")

    # Combine dataframes together
    gender["variable2"] = "Sex"
    ethnicity["variable2"] = "Ethnicity"
    age["variable2"] = "Age"

    return pd.concat([gender, ethnicity, age])

# Connect to database
conn = PostgresConnection(app=SERVER, tunnel=True, via_app=True)
sessionmaker = conn.session_maker()
single_quarter_cohorts = []


with sessionmaker() as session:    
    # Get some mapping to relation sending facilities to regions
    region_map = map_codes("RR1", "URTS_region", session)
    facility_names = lookup_codes("RR1+", "description", session)
    for facility in FACILITIES:
        for quarter in range(1,5):
            # calculate start and end from quarter and year
            quarter_start = dt.datetime(YEAR, quarter*3-2, 1)
            if quarter < 4:
                quarter_end = dt.datetime(YEAR, quarter*3 +1, 1) - dt.timedelta(days=1)
            else:
                quarter_end = dt.datetime(YEAR, 12, 31) 
            
            # Extract data and add additional labels
            try:
                tableau_demog = calculate_tableau_demog(facility, 
                    quarter_start, 
                    quarter_end, 
                    session
                )
            except NoCohortError:
                continue

            if tableau_demog is None:
                continue
            else:
                tableau_demog["year"] = YEAR
                tableau_demog["quarter"] = quarter
                tableau_demog["centre_code"] = facility
                tableau_demog["option"] = "Number"
                tableau_demog["country"] = "England"
                tableau_demog["measure"] = "Demography"
                tableau_demog["region"] = region_map.get(facility, "not in mapping")
                tableau_demog["centre"] = facility_names.get(facility, "not in mapping")
                tableau_demog["satellite"] = tableau_demog["satellite_code"].map(facility_names)
                tableau_demog.loc[tableau_demog["satellite"].isna(), "satellite"] = "not in mapping"
                single_quarter_cohorts.append(tableau_demog)

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
    "vascularaccess",
    "value"
]

print("\nWriting to file...")
combined_cohort = pd.concat(single_quarter_cohorts)
if not combined_cohort.empty:
    combined_cohort.to_csv(
        os.path.join(OUTPUT_DIR, OUTPUT_FILE), 
        index=False,
        columns=output_order
    )
else:
    raise ValueError("No data extracted")