"""
Base cohort functions
These functions define a set of core shared definitions which allow the
generation of cohorts from the ukrdc database to 
"""

from sqlalchemy.orm import Session
from ukrdc_stats.cohorts.query import query_ckd
from ukrdc_stats.labellers.demographics import age, adult_paed
from ukrdc_stats.labellers.biomarkers import egfr
from ukrdc_stats.utils.data import GENDER_GROUP_MAP
import datetime as dt
import pandera.pandas as pa

from ukrdc_stats.cohorts.schema import ckd_prevalent_schema


def ckd_incident(session: Session, facility: str, end: dt.datetime, start: dt.datetime):
    pass


@pa.check_output(ckd_prevalent_schema)
def ckd_prevalent(
    session: Session, facility: str, prevalence_point: dt.datetime
) -> ckd_prevalent_schema:
    """
    Get the prevalent CKD cohort for a given facility and prevalence point.

    Note: Should this be more by centre?

    Args:
        session (Session): UKRDC session
        facility (str): Facility code
        prevalence_point (dt.datetime): Prevalence point
    """

    # Get base data
    ukrdc_base_data = query_ckd(session, facility, prevalence_point)

    # Label patients
    ukrdc_base_data = age(ukrdc_base_data, prevalence_point)
    ukrdc_base_data = adult_paed(ukrdc_base_data)
    ukrdc_base_data = egfr(session, ukrdc_base_data, prevalence_point)

    # Apply cohort filtering logic
    cohort = (
        ukrdc_base_data[
            (ukrdc_base_data.adult_paed == "Adult")
            & (ukrdc_base_data.egfr_min < 30)
            & ~ukrdc_base_data.egfr_min.isna()
        ]
        .copy()
    )

    # label clinic types
    cohort.loc[:, "clinictype"] = cohort["admitreasoncode"].replace(
        {"902": "AKC", "903": "NEPH"},
    )
    cohort.loc[~cohort["clinictype"].isin(["AKC", "NEPH"]), "clinictype"] = "Other"

    cohort.loc[:, "sex"] = cohort["sex"].map(GENDER_GROUP_MAP).fillna("Missing")

    # fill na ethnicities
    cohort.loc[:, "ukkaethnicity"] = cohort["ukkaethnicity"].fillna("Missing")

    return cohort


def krt_prevalent():
    
    pass


def krt_incident():
    pass
  