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

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ukrdc_stats.calculators.krt import KRTStatsCalculator
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator, GENDER_GROUP_MAP
from ukrdc_stats.calculators.ckd import get_archive_session
from ukrdc_stats.utils import map_codes, lookup_codes, check_headcounts
from ukrdc_stats.exceptions import NoCohortError

from ukrdc_sqla.xmlarchive import Assessment, Patient
from ukrdc_sqla.ukrdc import PatientNumber, PatientRecord, DialysisSession

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

OUTPUT_FILE = "krt_care_planning"
SERVER =  "ukrdc_live"
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

### Start of cohort generating and then aggregating functions


### End of cohort generating and then aggregating functions

### Main routine
# Connect to database
if UKRDC_URL:
    ukrdc_session = sessionmaker(create_engine(UKRDC_URL))()
else:
    ukrdc_conn = PostgresConnection(app = SERVER, tunnel = True, via_app = True)
    ukrdc_sessionmaker = ukrdc_conn.session_maker()
    ukrdc_session = ukrdc_sessionmaker()

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