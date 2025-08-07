"""
ITSM-1052
Extracts dialysis prescriptions for active patients over a whole year. This
script currently doesn't reference the calculators but might in the future.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
import pandas as pd
import os
from pathlib import Path
import datetime as dt
from sqlalchemy import or_

from rr_connection_manager import PostgresConnection
from ukrdc_sqla.ukrdc import PatientRecord, PatientNumber, Treatment
from ukrdc_sqla.xmlarchive import Patient, DialysisPrescription
from ukrdc_stats.calculators.ckd import get_archive_session

# Configuration
YEAR = 2025
OUTPUT_DIR = Path("Q:")/ Path("Statisticians")/ Path("Dialysis prescription")
FILE_STEM = "dialysis_prescriptions"
SERVER =  "ukrdc_live"
FACILITIES = ["RCSLB", "RH8", "RK7CC", "RHW01", "RAQ01"]
os.makedirs(OUTPUT_DIR, exist_ok=True)

def cohort_definition(year:int, facility:str, ukrdc_session:Session):
    start_date = dt.datetime(year-1,12,31,0,0,0)
    #end_date = dt.datetime(year,12,31,0,0,0)
    end_date = dt.datetime(year,3,31,0,0,0)
    query = (
        select(PatientNumber.pid, PatientNumber.patientid, PatientNumber.organization)
            .join(PatientRecord, PatientNumber.pid == PatientRecord.pid)
            .join(Treatment, PatientNumber.pid == Treatment.pid)
            .where(
                Treatment.fromtime < end_date, 
                or_(
                    Treatment.totime > start_date,
                    Treatment.totime.is_(None),
                ),
                PatientRecord.sendingfacility == facility
            )
    )

    return pd.DataFrame(ukrdc_session.execute(query))

def extract_dialysis_prescriptions(facility:str, archive_session:Session):
    query = (
        select(
            Patient.nationalid, 
            Patient.organization, 
            DialysisPrescription.fromtime, 
            DialysisPrescription.totime, 
            DialysisPrescription.sessiontype, 
            DialysisPrescription.sessionsperweek,
            DialysisPrescription.timedialysed,
            DialysisPrescription.vascularaccess
        )
        .join(Patient, DialysisPrescription.patientid == Patient.id)
        .where(
            Patient.sendingfacility == facility,
        )
    )
    return pd.DataFrame(archive_session.execute(query)).rename(columns={"nationalid": "patientid"})


ukrdc_conn = PostgresConnection(app = SERVER, tunnel = True, via_app = True)
ukrdc_sessionmaker = ukrdc_conn.session_maker()

with ukrdc_sessionmaker() as ukrdc_session:
    archive_session = get_archive_session(ukrdc_session)
    for facility in FACILITIES:
        print(f"Extracting dialysis prescriptions for facility: {facility}")
        cohort = cohort_definition(YEAR, facility, ukrdc_session)
        dialysis_prescriptions = extract_dialysis_prescriptions(facility, archive_session)
        if dialysis_prescriptions.empty:
            with open(os.path.join(OUTPUT_DIR, f"{FILE_STEM}_{facility}_{YEAR}_ERROR.txt"), "w") as f:
                f.write(f"No dialysis prescriptions found for facility {facility}")
            continue

        # join cohorts together and deduplicate on pid and prescription data 
        cohort = pd.merge(cohort, dialysis_prescriptions,on = ("patientid","organization"), how="left")
        cohort.sort_values(by = ['pid', 'fromtime', 'organization'], ascending=[True, False, True], inplace=True)
        cohort.drop_duplicates(subset=['pid', 'fromtime', 'totime', 'sessiontype'], inplace=True)        
        cohort.to_csv(os.path.join(OUTPUT_DIR, f"{FILE_STEM}_{facility}_{YEAR}.csv"), index=False)
    archive_session.close()