import pandas as pd
import datetime as dt
from pathlib import Path
from dotenv import dotenv_values

from ukrdc_stats.utils.data import map_codes, lookup_codes
from ukrdc_stats.cohorts.base import krt_incident, krt_prevalent
from ukrdc_stats.labellers.demographics import age, adult_paed
from ukrdc_stats.labellers.geography import imd
from ukrdc_stats.labellers.clinical import vascular_access
from ukrdc_stats.utils.database import get_sessionmaker
from ukrdc_stats.utils.data import aggregate_data


config = dotenv_values(".env")
KEYPATH = config.get("UKRDC_STATS_KEYPATH")

YEAR_START: int = 2024
QUARTER_START: int = 1
NO_OF_QUARTERS: int = 8
OUTPUT_DIR: Path = ".do_not_commit" 
OUTPUT_FILE: str = "krt_demog.csv"
SERVER: str = "ukrdc_live"

FACILITIES = [
    # live
    "RAJ",   # MSE
    "RAQ01", # Lister
    "RCSLB", # Nottingham
    "RH8",   # RD&E
    "RHW01", # Reading
    "RK7CC", # Sheffield
    "RL403", # Wolverhampton
    "RNJ00", # Barts
    "RFPFG", # Derby
    "RBD01", # Dorset
    "RLZ01", # Shrewsbury
    "RP5",   # Doncaster
    "BHLY",  # BHLY
]
   

def main():
    with get_sessionmaker(SERVER, keypath=KEYPATH)() as session:
        region_map = map_codes("RR1", "URTS_region", session)
        facility_names = lookup_codes("RR1+", "description", session)
        for quarter in range(QUARTER_START - 1, QUARTER_START + NO_OF_QUARTERS - 1):
            # Calculate the start and end times to calculate for
            current_quarter = (quarter % 4) + 1
            current_year = YEAR_START + quarter // 4
            quarter_start = dt.datetime(current_year, current_quarter * 3 - 2, 1)
            if current_quarter < 4:
                quarter_end = dt.datetime(
                        current_year, current_quarter * 3 + 1, 1
                    ) - dt.timedelta(days=1)
            else:
                quarter_end = dt.datetime(current_year, 12, 31)

            krt_incident_combined = pd.DataFrame()
            krt_prevalent_combined = pd.DataFrame()
            for FACILITY in FACILITIES:
                # Extract incident and label
                krt_incident_report = krt_incident(session, FACILITY, quarter_end, quarter_start)
                krt_incident_report = age(krt_incident_report, quarter_end)
                krt_incident_report = adult_paed(krt_incident_report)
                krt_incident_report = vascular_access(krt_incident_report, session, quarter_end)
                krt_incident_report = imd(session, krt_incident_report)
                krt_incident_report["incidprev"] = "incident"
                krt_incident_combined = pd.concat([krt_incident_combined, krt_incident_report])
        
                # Extract prevalent and label
                krt_prevalent_report = krt_prevalent(session, FACILITY, quarter_end)
                krt_prevalent_report = age(krt_prevalent_report, quarter_end)
                krt_prevalent_report = adult_paed(krt_prevalent_report)
                krt_prevalent_report = vascular_access(krt_prevalent_report, session, quarter_end)
                krt_prevalent_report = imd(session, krt_prevalent_report)
                krt_prevalent_report["incidprev"] = "prevalent"
                krt_prevalent_combined = pd.concat([krt_prevalent_combined, krt_prevalent_report])
            
            # add year and quarter
            krt_prevalent_combined["year"] = current_year
            krt_prevalent_combined["quarter"] = current_quarter
            krt_incident_combined["year"] = current_year
            krt_incident_combined["quarter"] = current_quarter
    
    combined = pd.concat([krt_prevalent_combined, krt_incident_combined])
    combined["dialtplt_dup"] = combined["dialtplt"]
    output = aggregate_data(
        cohort_wide = combined,
        column_attributes = [
            "centre_code",
            "satellite_code",
            "adult_paed",
            "dialtplt_dup",
            "year",
            "quarter",
            "incidprev"
        ],
        row_attributes = [
            "age",
            "imddecile",
            "access", 
            "dialtplt"
        ]     
    )
    output.rename(columns = {"dialtplt_dup": "dialtplt"}, inplace=True)

    print(output.head())


if __name__ == "__main__":
    main()