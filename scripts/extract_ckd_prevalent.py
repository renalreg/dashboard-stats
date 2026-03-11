from ukrdc_stats.cohorts.base import ckd_prevalent
from ukrdc_stats.labellers.geography import imd
from ukrdc_stats.utils.data import aggregate_data
from ukrdc_stats.utils.database import get_sessionmaker
import datetime as dt
import os
from dotenv import load_dotenv

SERVER = "ukrdc_staging"
CENTRE = "RCSLB"

load_dotenv()   
KEYPATH = os.environ.get("UKRDC_STATS_KEYPATH")
if not KEYPATH:
    raise RuntimeError(
        "Missing UKRDC_STATS_KEYPATH. Set it in your environment or in a .env file."
    )
prevalence_date = dt.datetime(2025, 10, 1)

with get_sessionmaker(SERVER, keypath=KEYPATH)() as session:
    base_cohort = ckd_prevalent(session, CENTRE, prevalence_date)
    base_cohort = imd(session, base_cohort)    

    # only keep needed columns
    base_cohort = base_cohort[
        [
            "ukrdcid",
            "sendingfacility",
            "healthcarefacilitycode",
            "sex",
            "age",
            "clinictype",
            "ukkaethnicity",
            "imddecile"
        ]
    ]
    

    aggregated_data = aggregate_data(base_cohort, ["sendingfacility", "healthcarefacilitycode", "clinictype"])
    print(aggregated_data)
    
    #print(base_cohort)