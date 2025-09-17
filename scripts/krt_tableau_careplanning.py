"""
Example of how to extend the dashboard stats functionality using pandas to
produce an extract which is compatible with the tableau visualisations on the
UKKidney website here:
https://www.ukkidney.org/audit-research/data-portals

Hosted here:
https://public.tableau.com/app/profile/ukkidney/viz/KRTlandingpage/Landingpage

This functionality is still very much in development so it should be treated
with care yada yada.
"""

import datetime as dt
import os
import pandas as pd
from pathlib import Path

from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.krt import KRTStatsCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator, GENDER_GROUP_MAP
from ukrdc_stats.calculators.ckd import get_archive_session
from ukrdc_stats.utils import map_codes, lookup_codes
from sqlalchemy import select
from ukrdc_sqla.xmlarchive import Assessment, Patient
from ukrdc_sqla.ukrdc import PatientNumber, PatientRecord


# Configuration
YEAR = 2024
#OUTPUT_DIR = Path("Q:") / Path("UKRDC") / Path("UKRDC_Dashboard")
OUTPUT_DIR = Path(".do_not_commit")
OUTPUT_FILE = "tableau_krt_care_planning.csv"
SERVER =  "ukrdc_live"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FACILITIES = [
    "RCSLB"    
]

def get_facility_assessments(ukrdc_session, facility):
    """Get all assessments for a facility and link to the ukrdc patient records

    Args:
        archive_session (_type_): _description_
        facility (_type_): _description_

    Returns:
        _type_: _description_
    """
    archive_session = get_archive_session(ukrdc_session)

    # get assessments for facility
    query = select(
        Patient.nationalid,
        Patient.organization,
        Assessment.assessmentstart,
        Assessment.assessmentend,
        Assessment.assessmentoutcomecode
    ).join(
        Patient, Assessment.patientid == Patient.id
    ).where(
        Patient.sendingfacility == facility, 
        Assessment.assessmentoutcomecode.in_(["1", "2", "3"]),
        Assessment.assessmenttypecode == "TPLTassess"
    )
    assessments = pd.DataFrame(archive_session.execute(query))

    # get pids to link to the ukrdc patients 
    query = select(
        PatientNumber.pid,
        PatientNumber.patientid,
        PatientNumber.organization
    ).distinct(
        PatientNumber.pid,
        PatientNumber.patientid,
        PatientNumber.organization
    ).join(
        PatientRecord, PatientNumber.pid == PatientRecord.pid
    ).where(
        PatientRecord.sendingfacility == facility
    )
    pids = pd.DataFrame(ukrdc_session.execute(query))
    pids.rename(columns={"patientid":"nationalid"}, inplace=True)

    # link assessments to pids
    assessments = pd.merge(assessments, pids, on=["nationalid", "organization"], how="left")
    assessments.drop(columns=["organization", "nationalid"], inplace=True)

    assessments["assessmentoutcomecode"] = assessments["assessmentoutcomecode"].map({"1":"Unsuitable", "2":"In-progress", "3":"Suitable"})

    return assessments.drop_duplicates()

def krt_care_planning_cohort(assessments, ukrdc_session, facility, year, quarter):
    """Function to define the krt/careplanning cohort
    """
    quarter_start = dt.datetime(year, quarter*3-2, 1)
    if quarter < 4:
        quarter_end = dt.datetime(year, quarter*3 +1, 1) - dt.timedelta(days=1)
    else:
        quarter_end = dt.datetime(year, 12, 31) 
    
    
    krt_calculator = KRTStatsCalculator(
        session=ukrdc_session, 
        facility=facility, 
        from_time=quarter_start, 
        to_time=quarter_end
    )

    # create reports on incident and prevalent patients
    incident_krt_report = (
        krt_calculator.generate_cohort_report(
            cohort="incident"
        ).table.to_pandas()
    )
    incident_krt_report["incidprev"] = "Incident"
     

    # Mash them together and do some remapping 
    incident_krt_report.rename(
        columns = {"registry_code_type":"dialtplt",
        "sendingfacility":"centre_code",
        "healthcarefacilitycode":"satellite_code"},
        inplace=True
    )
    incident_krt_report["dialtplt"] = incident_krt_report["dialtplt"].map({"PD":"PD","TX":"Transplant","HD":"HD"})


    # Now we get the most recent assessment prior to the treatment start
    incident_krt_report = pd.merge(incident_krt_report, assessments, on="pid", how="left")
    incident_krt_report = incident_krt_report[incident_krt_report.assessmentstart < incident_krt_report.fromtime]

    incident_krt_report = incident_krt_report.sort_values(by=['pid', 'assessmentstart'], ascending=[True, False])
    incident_krt_report = incident_krt_report.drop_duplicates(subset=['pid'], keep='first')

    incident_krt_report.drop(columns = ["pid", "assessmentstart","assessmentend","admitreasoncode","admitreasoncodestd"], inplace=True)
    incident_krt_report.fillna("No assessment", inplace=True)
    
    return incident_krt_report

def apply_demographic_aggregation(cohort,ukrdc_session,facility,date):
    """
    Function to aggregate demographics data in a tableau digestible way
    """

    # initialise demographics and create report
    demographics_calculator = DemographicStatsCalculator(
        session=ukrdc_session,
        facility=facility,
        date = date
    )
    _, demographics_report = demographics_calculator.produce_report(
        output_columns=["gender", "age", "ethnic_group_code"]
    )
    demographics_report = demographics_report.to_pandas()
   
#    demographics_report["adultpaed"] = demographics_report["age"].astype(int) > 18 
#    demographics_report["adultpaed"] = demographics_report["adultpaed"].map({True: "Adult", False: "Paediatric"})
    demographics_report["adultpaed"] = 'Adult'

    # Aggregate gender
    gender = pd.merge(cohort, demographics_report[["ukrdcid","gender", "adultpaed"]], on="ukrdcid")
    gender["variable"] = gender["gender"].map(GENDER_GROUP_MAP)
    gender.drop(columns = ["gender"], inplace=True)
    gender.drop_duplicates(inplace=True)
    gender = gender.groupby(["satellite_code", "incidprev", "variable", "adultpaed", "dialtplt", "assessmentoutcomecode"]).size().reset_index(name="value")

    # Aggregate age 
    age = pd.merge(cohort, demographics_report[["ukrdcid","age", "adultpaed"]], on="ukrdcid")
    age["value"] = age["age"].astype(int)
    bins = [18, 25, 35, 45, 55, 65, 75, 85, 150]
    labels = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", ">=85"]
    age["variable"] = pd.cut(age["value"], bins=bins, labels=labels, right=False)
    age.drop_duplicates(inplace=True)
    age = age.groupby(["satellite_code", "incidprev", "variable", "adultpaed", "dialtplt", "assessmentoutcomecode"]).size().reset_index(name="value")

    # Aggregate ethnicity
    ethnic_group_map = map_codes("NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", ukrdc_session)
    ethnicity = pd.merge(cohort, demographics_report[["ukrdcid","ethnic_group_code", "adultpaed"]], on="ukrdcid")
    ethnicity["variable"] = ethnicity["ethnic_group_code"].map(ethnic_group_map)
    ethnicity.drop(columns = ["ethnic_group_code"], inplace=True )
    ethnicity.drop_duplicates(inplace=True)
    ethnicity = ethnicity.groupby(["satellite_code", "incidprev", "variable", "adultpaed", "dialtplt", "assessmentoutcomecode"]).size().reset_index(name="value")

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
        assessments = get_facility_assessments(session, facility)
        for quarter in range(1,5):
            # calculate start and end from quarter and year
            granular_cohort =  krt_care_planning_cohort(assessments, session, facility, YEAR, quarter)
            cohort = apply_demographic_aggregation(granular_cohort, session, facility, dt.datetime(YEAR, 12, 31, 23, 59, 59))
            
            cohort["year"] = YEAR
            cohort["quarter"] = quarter
            cohort["option"] = "Number"
            cohort["country"] = "England"
            cohort["measure"] = "Demography"
            cohort["region"] = region_map.get(facility, "not in mapping")
            cohort["centre_code"] = facility
            cohort["centre"] = facility_names.get(facility, "not in mapping")
            single_quarter_cohorts.append(cohort)

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
    "assessmentoutcomecode",
    "value",
]



pd.concat(single_quarter_cohorts).to_csv(
    os.path.join(OUTPUT_DIR, OUTPUT_FILE), 
    index=False
)