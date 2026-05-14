"""
Script to generate cohort for the ukrdc tableau dashboards.
"""
from ukrdc_stats.utils.database import get_sessionmaker
from ukrdc_stats.utils.data import map_codes, lookup_codes
from ukrdc_stats.cohorts.base import ckd_prevalent
from ukrdc_stats.exceptions import EmptyCohortError
from dotenv import dotenv_values
import pandas as pd
import datetime as dt

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

FACILITIES = [
# live
"RAJ",   # MSE
"RAQ01", # Lister
]

config = dotenv_values(".env")
KEYPATH = config.get("UKRDC_STATS_KEYPATH")

YEAR_START = 2024
QUARTER_START = 1
NO_OF_QUARTERS = 8
SERVER = "ukrdc_live"
OUTPUT_FILE = "ckd_demog"
OUTPUT_FILE = f"{OUTPUT_FILE}_{SERVER}_{YEAR_START}.csv"

def main():
    with get_sessionmaker(SERVER, keypath=KEYPATH)() as session:
        region_map = map_codes("RR1", "URTS_region", session)
        facility_names = lookup_codes("RR1+", "description", session)
        print("Extracting cohort for facility: ")
        patients = []
        for facility in FACILITIES:
            print(facility)
            quarter_index_start = QUARTER_START - 1
            quarter_index_end = QUARTER_START + NO_OF_QUARTERS - 1
            for quarter in range(quarter_index_start, quarter_index_end):
                # extract set of labelled patients for each center, year, quarter
                current_quarter = (quarter % 4) + 1
                current_year = YEAR_START + quarter // 4
                try:
                    unaggregated_cohort = ckd_prevalent(session, facility, dt.datetime(current_year, current_quarter * 3, 1))
                except EmptyCohortError:
                    print(f"No patients found for facility {facility} in quarter {current_quarter} {current_year}")
                    continue

                unaggregated_cohort["quarter"] = current_quarter
                unaggregated_cohort["year"] = current_year
                patients.append(unaggregated_cohort)
        
        if patients:
            patient_all = pd.concat(patients)
            patient_all["country"] = "England"
            patient_all["centre"] = patient_all["centre_code"].map(
                facility_names
            )
            patient_all["region"] = patient_all["centre_code"].map(region_map)
            patient_all["satellite"] = patient_all["satellite_code"].map(
                facility_names
            )
            patient_all = patient_all.rename(columns= {
                "gender": "Sex",
                "ethnicity": "Ethnicity",
                "agecat": "Age",
                "clinic_type": "Clinic Type",
            })
    
if __name__ == "__main__":
    main()