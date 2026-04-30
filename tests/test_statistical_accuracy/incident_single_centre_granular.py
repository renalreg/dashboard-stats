"""This is a manual test to check the totals calculated by the calculator 
functions against know totals from UKKA published ckd demographics data.
"""
from ukrdc_stats.cohorts.base import krt_incident
from ukrdc_stats.utils.database import get_sessionmaker
from ukrdc_stats.utils.query import pid_ni_map
import datetime as dt
import pandas as pd
from dotenv import dotenv_values
from pathlib import Path





FACILITY = "RCSLB"
SERVER = "ukrdc_live"
YEAR = 2022

config = dotenv_values(".env")
KEYPATH = config.get("UKRDC_STATS_KEYPATH")

rr_incident_data = Path(f".do_not_commit/rr_unaggregated/{FACILITY}_incident_{YEAR}.csv")
rr_ref_data = pd.read_csv(rr_incident_data)

if not KEYPATH:
    raise RuntimeError(
        "Missing UKRDC_STATS_KEYPATH. Set it in your environment or in a .env file."
    )
    
start_date = dt.datetime(YEAR-1, 12, 31)
end_date = dt.datetime(YEAR, 12, 31)

with get_sessionmaker(SERVER, keypath=KEYPATH)() as session:
    pid_map = pid_ni_map(session, [FACILITY])
    pid_map = pid_map[pid_map.organization.isin(["NHS", "CHI", "HSC"])]
    rr_ref_data = rr_ref_data.merge(pid_map, left_on="NHSno", right_on="patientid", how="left")
    rr_ref_data = rr_ref_data[["pid", "NHSno", "KRT-start", "centre", "trt-start"]]
    incident_cohort = krt_incident(session, FACILITY, start_date=start_date, end_date=end_date)
    incident_cohort = incident_cohort.merge(rr_ref_data, left_on="pid", right_on="pid", how="left").sort_values("dialtplt")
    
    print(":)")

    
#    centre_cohort = krt_incident(session, FACILITY, start_date=dt.datetime(2023, 1, 1), end_date=dt.datetime(2023, 12, 31))
#    centre_cohort = centre_cohort[centre_cohort["centre_code"] == FACILITY]
