"""
Creates an extract of dialysis sessions following a cohort of prevalent
patients over a year.
"""


import os
from pathlib import Path

import datetime as dt
import pandas as pd
from dotenv import dotenv_values
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from ukrdc_stats.calculators.krt import KRTStatsCalculator
from ukrdc_stats.calculators.ckd import get_archive_session

from ukrdc_sqla.xmlarchive import DialysisPrescription, Patient as ArchivePatient
from ukrdc_sqla.ukrdc import PatientRecord, PatientNumber, DialysisSession, Address, Patient
from sqlalchemy import select, func, case, or_


# Configuration
YEAR = 2022 # prevalent at end of this year

OUTPUT_DIR = Path("Q:")/ Path("Statisticians")/ Path("Dialysis prescription")
#OUTPUT_DIR = Path(".do_not_commit")
FILE_STEM = "dialysis_prescriptions_combined"
SERVER =  "ukrdc_live"
FACILITIES = ["RCSLB", "RH8", "RK7CC", "RHW01", "RAQ01", "RL403"]
#FACILITIES = ["RCSLB"]
os.makedirs(OUTPUT_DIR, exist_ok=True)
CONFIG = dotenv_values(".env")
UKRDC_URL = CONFIG["ukrdc_url"] 
session = sessionmaker(create_engine(UKRDC_URL))()


# Get prevalent patients
prevalent_dfs = []
for facility in FACILITIES:    
    # get prevalent demographics
    krt_calculator = KRTStatsCalculator(
        session=session, 
        facility=facility,
        from_time = dt.datetime(YEAR,1,1,0,0,0), 
        to_time = dt.datetime(YEAR,12,31,0,0,0),
    )
    krt_report = krt_calculator.generate_cohort_report(cohort="prevalent", include_ni=True)
    prevalent_df = krt_report.table.to_pandas()
    rename_map = {
        "pid": "pid",
        "healthcarefacilitycode": "satellitecode",
        "registry_code_type": "modality",
        "nhsno": "nhsno",
    }

    prevalent_df = prevalent_df.rename(columns=rename_map)[list(rename_map.values())].drop_duplicates()
    prevalent_dfs.append(prevalent_df)

prevalent_cohort = pd.concat(prevalent_dfs)


"""
Build supporting datasets: patient numbers for ID linking and a single-row demographics view per PID.
"""
# get patient numbers and other demogs
pids = prevalent_cohort.pid.drop_duplicates().tolist()
chunk_size = 1000
patient_numbers = []
patient_demogs = []
for i in range(0, len(pids), chunk_size):
    # get patient numbers
    query = select(
        PatientNumber.pid,
        PatientNumber.patientid,
        PatientNumber.organization,
        PatientNumber.numbertype,
    ).where(
        PatientNumber.pid.in_(pids[i:i+chunk_size]),
    )
    patient_numbers.append(pd.DataFrame(session.execute(query).mappings().all()).drop_duplicates())

    # get demographics (one best address per PID)
    address_ranked = (
        select(
            Address.pid,
            Address.postcode,
            Address.addressuse,
            func.row_number()
            .over(
                partition_by=Address.pid,
                order_by=case((Address.addressuse == "H", 0), else_=1),
            )
            .label("rn"),
        ).where(Address.postcode.is_not(None), func.trim(Address.postcode) != "")
    ).subquery()

    query = select(
        Patient.pid,
        Patient.ethnicgroupcode,
        Patient.ethnicgroupcodestd,
        Patient.ethnicgroupdesc,
        address_ranked.c.postcode,
        address_ranked.c.addressuse,
        Patient.gender.label("Sex"),
        Patient.birthtime,
    ).outerjoin(
        address_ranked, 
        address_ranked.c.pid == Patient.pid
    ).where(
        Patient.pid.in_(pids[i:i+chunk_size]),
        or_(address_ranked.c.rn == 1, address_ranked.c.rn.is_(None)),
    )
    patient_demogs.append(pd.DataFrame(session.execute(query).mappings().all()).drop_duplicates())

# concatenate and clean
combined_demogs = pd.concat(patient_demogs).reset_index(drop=True)
combined_patient_numbers = pd.concat(patient_numbers).reset_index(drop=True)
combined_demogs["Sex"] = combined_demogs["Sex"].map({"1": "Male", "2": "Female"})


# Create pid -> nhsno mapping
pid_to_nhs = (
    combined_patient_numbers[combined_patient_numbers["organization"] == "NHS"][
        ["pid", "patientid"]
    ]
    .drop_duplicates()
    .rename(columns={"patientid": "nhsno"})
)

# Build demographics sheet by joining cohort basics with demographics and NHS numbers
demographics_df = (
    prevalent_cohort[["pid", "satellitecode", "modality"]]
    .drop_duplicates()
    .merge(combined_demogs, on="pid", how="left")
    .merge(pid_to_nhs, on="pid", how="left")
)


# rename and reorder columns
demographics_df = demographics_df.rename(columns={
    "satellitecode": "Centre",
    "modality": "RRT Modality",
    "nhsno": "NHS Number",
    "ethnicgroupcode": "Ethnic Group Code",
    "ethnicgroupdesc": "Ethnic Group Description",
    "postcode": "Postcode",
    "birthtime": "Date of Birth",
})
demographics_df["Date of Birth"] = pd.to_datetime(demographics_df["Date of Birth"]).dt.date

demographics_df = demographics_df[
    [
        "NHS Number",
        "Date of Birth",
        "Centre",
        "RRT Modality",
        "Sex",
        "Ethnic Group Code",
        "Ethnic Group Description",
        "Postcode",
    ]
]

"""
Dialysis prescriptions: query xml archive, map (nationalid, organization, numbertype) -> pid, then pid -> NHS.
Restrict to prescriptions overlapping the target year and to the prevalent cohort PIDs.
"""
archive_session = get_archive_session(session)

start_dt = dt.datetime(YEAR+1, 1, 1, 0, 0, 0)
end_dt = dt.datetime(YEAR+1, 12, 31, 23, 59, 59)

query_dialysis_prescriptions = (
    select(
        ArchivePatient.nationalid.label("patientid"),
        ArchivePatient.numbertype,
        ArchivePatient.organization,
        ArchivePatient.sendingfacility,
        DialysisPrescription.fromtime,
        DialysisPrescription.totime,
        #DialysisPrescription.sessiontype,
        DialysisPrescription.sessionsperweek,
        DialysisPrescription.timedialysed,
        DialysisPrescription.vascularaccess,
    )
    .join(DialysisPrescription, ArchivePatient.id == DialysisPrescription.patientid)
    .where(
        ArchivePatient.sendingfacility.in_(FACILITIES),
        DialysisPrescription.fromtime <= end_dt,
        or_(DialysisPrescription.totime >= start_dt, DialysisPrescription.totime.is_(None)),
    )
)
archive_presc = pd.DataFrame(archive_session.execute(query_dialysis_prescriptions).mappings().all()).drop_duplicates()

# Map archive patient identifiers -> pid using known patient numbers for the prevalent cohort
presc_with_pid = archive_presc.merge(
    combined_patient_numbers,
    left_on=["patientid", "organization", "numbertype"],
    right_on=["patientid", "organization", "numbertype"],
    how="left",
)

# Restrict to prevalent cohort PIDs only, then add NHS
presc_with_pid = presc_with_pid[presc_with_pid["pid"].isin(pids)]
dialysis_prescriptions = presc_with_pid.merge(pid_to_nhs, on="pid", how="left")

# Order columns for clarity
presc_cols = [
    "nhsno",
    "fromtime",
    "totime",
#    "sessiontype",
    "sessionsperweek",
    "timedialysed",
    "vascularaccess",
]
dialysis_prescriptions = dialysis_prescriptions[presc_cols].drop_duplicates()

# Transform dialysis prescription columns (hard-coded casing)
dialysis_prescriptions["Prescription Start Date"] = pd.to_datetime(dialysis_prescriptions["fromtime"]).dt.date
dialysis_prescriptions["Prescription End Date"] = pd.to_datetime(dialysis_prescriptions["totime"]).dt.date
dialysis_prescriptions = dialysis_prescriptions.drop(columns=["fromtime", "totime"])  # keep date-only
dialysis_prescriptions = dialysis_prescriptions.rename(
    columns={
        "nhsno" : "NHS Number",
        "sessionsperweek": "Times Per Week",
        "vascularaccess": "Vascular Access In Use",
        "sessiontype": "Dialysis Type",
        "timedialysed": "Time Dialysed",
    }
)

# Final column order
dialysis_prescriptions = dialysis_prescriptions[
    [
        "NHS Number",
        "Prescription Start Date",
        "Prescription End Date",
        #"Dialysis Type",
        "Times Per Week",
        "Time Dialysed",
        "Vascular Access In Use",
    ]
]


"""
Dialysis sessions: query main DB for sessions during the year for prevalent PIDs, then add NHS.
"""
query_dialysis_sessions = (
    select(
        PatientRecord.pid,
        PatientRecord.sendingfacility,
        DialysisSession.procedure_time,
        DialysisSession.qhd20,
        DialysisSession.qhd31,
        DialysisSession.procedure_type_code,
    )
    .join(PatientRecord, PatientRecord.pid == DialysisSession.pid)
    .where(
        PatientRecord.sendingfacility.in_(FACILITIES),
        DialysisSession.pid.in_(pids),
        DialysisSession.procedure_time >= start_dt,
        DialysisSession.procedure_time <= end_dt,
    )
)

dialysis_sessions = pd.DataFrame(session.execute(query_dialysis_sessions).mappings().all()).drop_duplicates()
dialysis_sessions = dialysis_sessions.merge(pid_to_nhs, on="pid", how="left")

# Transform raw data according to specifications (hard-coded casing)
dialysis_sessions["Haemodialysis or plasma exchange"] = dialysis_sessions["procedure_type_code"].map({"302497006": "HD", "19647005": "PX"})
dialysis_sessions["Date of HD/PEX Session"] = pd.to_datetime(dialysis_sessions["procedure_time"]).dt.date
dialysis_sessions["Clocktime Session Started"] = pd.to_datetime(dialysis_sessions["procedure_time"]).dt.strftime("%H:%M")
dialysis_sessions = dialysis_sessions.drop(columns=["procedure_type_code", "procedure_time", "pid"])
dialysis_sessions = dialysis_sessions.rename(
    columns={
        "sendingfacility":"Centre",
        "qhd20": "Vascular Access Used For This Treatment",
        "qhd31": "Duration Of Treatment In Minutes",
        "nhsno": "NHS Number"
    }
)
dialysis_sessions = dialysis_sessions[
    [
        "NHS Number",
        "Date of HD/PEX Session",
        "Clocktime Session Started",
        "Haemodialysis or plasma exchange",
        "Duration Of Treatment In Minutes",
        "Vascular Access Used For This Treatment",
        "Centre",
    ]
]


# Build a small parameters sheet
parameters_df = pd.DataFrame(
    {
        "Parameter": [
            "Database Server",
            "Facilities",
            "Prevalence Year (end-of-year)",
        ],
        "Value": [
            SERVER,
            ", ".join(FACILITIES),
            YEAR,
        ],
    }
)

# Write outputs to a 4-sheet Excel workbook
output_file = OUTPUT_DIR / f"{FILE_STEM}_{YEAR}.xlsx"
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # Preserve exact casing for prescriptions and sessions
    parameters_df.to_excel(writer, sheet_name="Parameters", index=False)
    demographics_df.to_excel(writer, sheet_name="Prevalent Cohort Demographics", index=False)
    dialysis_prescriptions.to_excel(writer, sheet_name="Dialysis Prescriptions", index=False)
    dialysis_sessions.to_excel(writer, sheet_name="Dialysis Sessions", index=False)
    


archive_session.close()
session.close()