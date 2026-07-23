"""
Base cohort functions
These functions define a set of core shared definitions which allow the
generation of cohorts from the ukrdc database to 
"""

from sqlalchemy.orm import Session
from typing import Optional

from ukrdc_stats.cohorts.query import query_ckd, query_krt_incident, query_krt_prevalent
from ukrdc_stats.labellers.demographics import age, adult_paed
from ukrdc_stats.labellers.biomarkers import egfr
from ukrdc_stats.labellers.geography import main_satellite_centres
from ukrdc_stats.utils.data import GENDER_GROUP_MAP

import numpy as np
import datetime as dt
import pandera.pandas as pa
import pandas as pd


from ukrdc_stats.cohorts.schema import ckd_prevalent_schema, krt_prevalent_schema, krt_incident_schema


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

    # Error handling for low completeness egfr
    if ukrdc_base_data["egfr_min"].sum() / ukrdc_base_data.shape[0] < 0.1:
        raise ValueError("Low completeness egfr")

    

    # Apply cohort filtering logic
    cohort = (
        ukrdc_base_data[
            (ukrdc_base_data.adult_paed == "Adult")
            & (ukrdc_base_data.egfr_min <= 15)
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

    # TODO: this deduplication logic should be revisited and was motivated by
    # patient with low clearance and nephrology clinic on the same day.
    cohort = cohort.sort_values(
        by=["ukrdcid", "fromtime", "admitreasoncode"],
        ascending=[True, False, False]
    ).drop_duplicates(subset=["ukrdcid"], keep="first")

    cohort = main_satellite_centres(session, cohort)
    
    return cohort


def _chain_treatments(base_cohort, recovery_window:dt.timedelta):
    """
 
    Args:
        base_cohort (_type_): _description_
        recovery_window (dt.timedelta): _description_
 
    Returns:
        _type_: _description_
    """
    
    base_cohort.sort_values(by=["ukrdcid", "fromtime", "totime"], inplace=True)
    base_cohort['timeline_order'] = base_cohort.groupby('ukrdcid').cumcount()
    
    # Get previous treatment's time bounds (within each patient)
    base_cohort['prev_fromtime'] = base_cohort.groupby('ukrdcid')['fromtime'].shift(1)
    base_cohort['prev_totime'] = base_cohort.groupby('ukrdcid')['totime'].shift(1)
    
    
    # Allen's 7 interval relationships with the recovery window absorbed into 
    # the defintions of "before" and "overlaps" i.e a record overlaps if it is 
    # within the recovery window of the previous record
    conditions = [
        # Before: previous (including recovery window) end is before current start
        base_cohort['prev_totime'] + recovery_window < base_cohort['fromtime'],

        # Short recovery: not in allen this is necessitated by the recovery window 
        # being applied to the "before" condition
        (base_cohort['prev_totime'] + recovery_window >= base_cohort['fromtime']) 
        & (base_cohort['prev_totime'] < base_cohort['fromtime']),

        # Meets: previous end equals current start
        (base_cohort['prev_totime'] == base_cohort['fromtime']) & (base_cohort['prev_fromtime'] != base_cohort['fromtime']),
        
        # Overlaps: previous starts before current, current starts before previous extended end, previous extended end before current end
        (base_cohort['prev_fromtime'] < base_cohort['fromtime']) &
        (base_cohort['prev_totime'] > base_cohort['fromtime']),
        
        # Starts: same start, previous ends before current
        (base_cohort['prev_fromtime'] == base_cohort['fromtime']) &
        (base_cohort['prev_totime'] < base_cohort['totime']),

        # Contains: current starts after previous, previous ends after current
        #(base_cohort['prev_fromtime'] < base_cohort['fromtime']) &
        #(base_cohort['totime'] < base_cohort['prev_totime']),

        # During: inverse of contains
        (base_cohort['prev_fromtime'] < base_cohort['fromtime']) &
        (base_cohort['totime'] < base_cohort['prev_totime']),
        
        # Finishes: previous starts after current, same end
        #(base_cohort['prev_fromtime'] > base_cohort['fromtime']) &
        #(base_cohort['prev_totime'] == base_cohort['totime']),

        # Finished by: inverse of above
        (base_cohort['prev_fromtime'] < base_cohort['fromtime']) &
        (base_cohort['prev_totime'] == base_cohort['totime']),
        
        # Equals: same start and end
        (base_cohort['prev_fromtime'] == base_cohort['fromtime']) &
        (base_cohort['prev_totime'] == base_cohort['totime'])
    ]
    
    choices = ['before',"short recovery", 'meets', 'overlaps', 'starts', 'during', 'finished by', 'equals']
    base_cohort['prev_treatment_relationship'] = np.select(conditions, choices, default=None)

    return base_cohort


def _clean_totime(base_cohort:pd.DataFrame) -> pd.DataFrame:
    """
    The current record will typically be open (totime is NaT). However it's 
    more convenient to treat these as infinities, for computing equalities.
    Function also cleans totimes where a date of death is present. This 
    function could further be expanded to handle cases where the record hasn't
    been closed. 
    
    Args:
        base_cohort (pd.DataFrame): Base cohort dataframe

    Returns:
        pd.DataFrame: Cleaned base cohort dataframe
    """

    # conveniently large number to represent infinity
    infinity = dt.datetime(2200, 1, 1)

    if 'totime' not in base_cohort.columns:
        raise ValueError("totime column not found in base_cohort")
    
    # Replace NaT with infinity
    base_cohort.loc[base_cohort['totime'].isna(), 'totime'] = infinity
    base_cohort.loc[base_cohort['deathtime'].isna(), 'deathtime'] = infinity

    if "deathtime" in base_cohort.columns:
        mask = base_cohort['totime'] >= base_cohort['deathtime']
        base_cohort.loc[mask, 'totime'] = base_cohort.loc[mask, 'deathtime']

    return base_cohort

def _clean_equal_records(base_cohort:pd.DataFrame) -> pd.DataFrame:
    """
    Remove records that are equal to the previous record.
    
    Args:
        base_cohort (pd.DataFrame): Base cohort dataframe
    
    Returns:
        pd.DataFrame: Cleaned base cohort dataframe
    """

    if 'prev_treatment_relationship' not in base_cohort.columns:
        raise ValueError("prev_treatment_relationship column not found in base_cohort")
    
    base_cohort.to_csv("equal_records_debug.csv", index=False)
    

    # Rule 1: where equal records of same modality are present in different 
    # centres merge records. This for cases where multiple centres fill in
    # treatment timeline
    equal_records = base_cohort[
        base_cohort['prev_treatment_relationship'] == 'equals'
    ]
    for record in equal_records.itertuples():
        # earlier iterations may already have dropped this record or its predecessor
        if record.Index not in base_cohort.index:
            continue
        prev_rows = base_cohort.loc[
            (record.ukrdcid == base_cohort.ukrdcid)
            & (record.timeline_order - 1 == base_cohort.timeline_order)
        ]
        if prev_rows.empty:
            continue
        # itertuples gives a single row object so comparisons yield scalars
        prev_record = next(prev_rows.itertuples())

        # if the centre of equal records isn't equal we attemp to keep the one
        # that matches the ckd centre. Note that we may want to expand this to
        # starts and contains as well
        if prev_record.sendingfacility != record.sendingfacility:
            ckd_centres = {
                c for c in (prev_record.ckd_centre, record.ckd_centre) if pd.notna(c)
            }
            prev_matches = prev_record.sendingfacility in ckd_centres
            curr_matches = record.sendingfacility in ckd_centres
            if prev_matches and not curr_matches:
                # Keep the previous record and remove the current one
                base_cohort = base_cohort.drop(record.Index)
            elif curr_matches and not prev_matches:
                # recode relationship and drop previous record
                base_cohort.loc[record.Index, 'prev_treatment_relationship'] = prev_record.prev_treatment_relationship
                base_cohort = base_cohort.drop(prev_record.Index)

    return base_cohort

def _label_timeline(krt_incident_cohort:pd.DataFrame) -> pd.DataFrame:
    """
    
    
    Args:
        krt_incident_cohort (pd.DataFrame): KRT incident cohort dataframe
        
    Returns:
        pd.DataFrame: KRT incident cohort dataframe with treatment labels
    """
    
    if 'prev_treatment_relationship' not in krt_incident_cohort.columns:
        raise ValueError("prev_treatment_relationship column not found in krt_incident_cohort")
    
    timeline_start = krt_incident_cohort[
        (krt_incident_cohort["prev_treatment_relationship"] == 'before')
        | krt_incident_cohort["prev_treatment_relationship"].isna()
    ][["ukrdcid", "fromtime"]].sort_values("fromtime", ascending=False).drop_duplicates("ukrdcid", keep="first")
    timeline_start.rename(columns={"fromtime": "timeline_start"}, inplace=True)

    timeline_stop = krt_incident_cohort[["ukrdcid", "totime"]].drop_duplicates("ukrdcid", keep="last")
    timeline_stop.rename(columns={"totime": "timeline_stop"}, inplace=True)

    timeline = timeline_start.merge(timeline_stop, on="ukrdcid", how="inner")
    timeline["timeline_length"] = timeline["timeline_stop"] - timeline["timeline_start"]
    
    krt_incident_cohort = krt_incident_cohort.merge(timeline, on="ukrdcid", how="left")
    krt_incident_cohort["length_of_life"] = krt_incident_cohort["deathtime"] - krt_incident_cohort["timeline_start"]
    
    return krt_incident_cohort

def _reassign_transplants(singular_cohort):
    """
    Transplants should be reassigned to their supervision centre as opposed to 
    the transplanting centre.

    TODO:
    1) How to handle unsuccessful transplants? 
    2) How to handle patients with no ckd centre?
    
    Args:
        singular_cohort (pd.DataFrame): Singular cohort dataframe
        full_cohort (pd.DataFrame): Full cohort dataframe
        
    Returns:
        pd.DataFrame: Singular cohort dataframe with transplants reassigned
    """

    # In instance of admissionsource we reassign 
    # how do we handle things like 999? 
    transfer_in_mask = (
        (singular_cohort.dialtplt == 'TX')
        & (singular_cohort.admissionsourcecode != singular_cohort.centre_code)
        & (singular_cohort.admissionsourcecode != "999")
        & (singular_cohort.admissionsourcecode!="ABROAD")
        & ~singular_cohort.admissionsourcecode.isna()
    )

    singular_cohort.loc[transfer_in_mask, "centre_code"] = singular_cohort.loc[transfer_in_mask, "admissionsourcecode"]
   
    return singular_cohort 

def _label_incident(krt_new_cohort, recovery_window:dt.timedelta= dt.timedelta(days=90)):
    """
    The UKRR incident cohort counts patients who are recieving acute and
    chronic dialysis differently. This function attempts to apply this 
    discrimination to ukrdc patients.    

    Returns:
        pd.DataFrame: DataFrame with acute/chronic labels
    """

    # anyone who receives a transplant at any point is coded as chronic as long
    #  as it doesn't fail within 14 days. This many not be precise enough
    group1_ids = krt_new_cohort[
      (krt_new_cohort.dialtplt == "TX")
        & ((krt_new_cohort.totime - krt_new_cohort.fromtime) > dt.timedelta(days=14))
    ].ukrdcid.unique()
    
    # code as chronic if on dialysis for greater than 90 days starting on dialysis
    group2_ids = krt_new_cohort[
        (krt_new_cohort.timeline_length > recovery_window)
        & (krt_new_cohort.fromtime == krt_new_cohort.timeline_start)
        & krt_new_cohort.dialtplt.isin(["PD", "HD"])
    ].ukrdcid.unique()
    
    # patients with ckd centre who die within 90 days we may need to verify with egfr
    group3_ids = krt_new_cohort[
        (krt_new_cohort.timeline_length < recovery_window)
        & (krt_new_cohort.length_of_life < recovery_window)
        & (krt_new_cohort.acute=="0")
        & krt_new_cohort.ckd_centre.notna()
    ].ukrdcid.unique()

    # Patients who's last treatment is a transfer out of type that implies they remain on treatment
    # TODO: include 85, 86? condition on length of life?
    group4_ids = krt_new_cohort[
        (krt_new_cohort.timeline_stop == krt_new_cohort.totime)
        & (krt_new_cohort.timeline_length < recovery_window) 
        & (krt_new_cohort.dischargereasoncode.isin(['38', '30', '91', '92']))
        & (krt_new_cohort.acute=="0")
    ].ukrdcid.unique()

    # filter down to chronic krt patients
    chronic_ids = set(group1_ids) | set(group2_ids) | set(group3_ids) | set(group4_ids)

    krt_new_cohort["incident"] = False
    krt_new_cohort.loc[krt_new_cohort["ukrdcid"].isin(chronic_ids), "incident"] = True
    
    return krt_new_cohort

def _label_incident_old(krt_new_cohort, start_date: dt.datetime, end_date: dt.datetime, recovery_window:dt.timedelta= dt.timedelta(days=90)):
    """Function with the aim of replicating the incident cohort produced by version 2.x.x here for testing purposes

    Args:
        krt_new_cohort (_type_): _description_
        recovery_window (dt.timedelta, optional): _description_. Defaults to dt.timedelta(days=90).
    """
    

    # transfer out patients
    discharge_reasons = []  # = ["38"]?
    discharge_locations = ["ABROAD"]
    transfered_patients = krt_new_cohort[
        (
            krt_new_cohort.dischargelocationcode.isin(discharge_locations)
            | krt_new_cohort.dischargereasoncode.isin(discharge_reasons)
        )
        & (krt_new_cohort.fromtime == krt_new_cohort.timeline_start)
    ].ukrdcid.drop_duplicates()
    transfered_out = krt_new_cohort.ukrdcid.isin(transfered_patients)

    # Crash landed patients are defined:
    # - no chronic treatment records or tx
    # - remains on KRT for more than 90 days or transfered out
    # - survives for more than 90 days
    is_crash_landing = (
        (krt_new_cohort.ckd_centre.isna()) & (krt_new_cohort.historic_tx.isna())
        & (
            (krt_new_cohort.timeline_length > recovery_window)
            | transfered_out
        )
        & (krt_new_cohort.length_of_life > recovery_window)
    )

    # Patients with a previous record of transplant or ckd are considered
    # planned for KRT. These patients must stay on KRT for more than 90
    # days or die to be counted as incident.
    planned_ckd = (~krt_new_cohort.ckd_centre.isna() | ~krt_new_cohort.historic_tx.isna()) & (
        (krt_new_cohort.timeline_length > recovery_window)
        | transfered_out
    ) | (krt_new_cohort.length_of_life < recovery_window)


    krt_new_cohort["incident"] = (
        (planned_ckd | is_crash_landing)
        & (krt_new_cohort.timeline_start > start_date)
        & (krt_new_cohort.timeline_start <= end_date)
    )

    # reduce down to one row per patient
    incident_cohort_singular = krt_new_cohort[
        krt_new_cohort.timeline_start == krt_new_cohort.fromtime
    ].sort_values("totime", ascending=False).drop_duplicates("ukrdcid", keep="first")

    return incident_cohort_singular


@pa.check_output(krt_incident_schema)
def krt_incident(
    session:Session, 
    facility:str, 
    end_date:dt.datetime, 
    start_date:Optional[dt.datetime] = None,
    recovery_window:dt.timedelta = dt.timedelta(days=90)
    ) -> krt_incident_schema:
    """
    Get the incident KRT cohort for a given facility and date range.

    Args:
        session (Session): UKRDC session
        facility (str): Facility code
        end_date (dt.datetime): End date
        start_date (Optional[dt.datetime], optional): Start date. If not set it will default to a year prior to the end date.

    """

    if not start_date:
        start_date = end_date - dt.timedelta(days=365)

    if start_date > end_date:
        raise ValueError("Start date must be before end date")
   
    # extract, clean and label the patient records used to calculate incidence
    base_cohort = query_krt_incident(session, facility, end_date, start_date, recovery_window)
    
    # debug 
    debug_ukrdcids = ['100133317']

    base_cohort = base_cohort[base_cohort.ukrdcid.isin(debug_ukrdcids)]
    base_cohort["dialtplt"] = base_cohort["registry_code_type"].copy() 
    base_cohort = _clean_totime(base_cohort)    
    base_cohort = _chain_treatments(base_cohort, recovery_window)
    base_cohort = _label_timeline(base_cohort)
    base_cohort = _clean_equal_records(base_cohort)

    # Remove patients with timelines beginning before analysis window or historic tx
    base_cohort = base_cohort[
        (base_cohort.timeline_start >= start_date)
        & (base_cohort.timeline_start <= end_date)
        & ~base_cohort.historic_tx
    ].copy()

    base_cohort = _label_incident(base_cohort, recovery_window)


    # reduce down to one row per patient
    singular_cohort = base_cohort[
        base_cohort.timeline_start == base_cohort.fromtime
    ].sort_values("totime", ascending=False).drop_duplicates("ukrdcid", keep="first")

    
    #singular_incident = _label_incident_old(base_cohort, start_date, end_date, recovery_window)
    singular_cohort = main_satellite_centres(session, singular_cohort, outlier_mapping_mode="otherise")
    singular_cohort = _reassign_transplants(singular_cohort)

    return singular_cohort[singular_cohort.incident & (singular_cohort.centre_code == facility)]

@pa.check_output(krt_prevalent_schema)
def krt_prevalent(session: Session, facility: str, prevalence_point: dt.datetime) -> krt_prevalent_schema:
    """
    Get the prevalent KRT cohort for a given facility and prevalence point.
    
    Returns:
        krt_prevalent_schema: Prevalent KRT cohort
    """

    base_cohort = query_krt_prevalent(session, facility, prevalence_point)
    base_cohort["dialtplt"] = base_cohort["registry_code_type"]

    # TODO: more logic around recovey window and treatment relationship to prevalence point
    singular_cohort = (
        base_cohort[
            (base_cohort.fromtime <= prevalence_point)
            & ((base_cohort.totime > prevalence_point) | base_cohort.totime.isna())
        ]
        .sort_values("totime", ascending=False)
        .drop_duplicates("ukrdcid", keep="first")
    )   

    singular_cohort = main_satellite_centres(session, singular_cohort, outlier_mapping_mode="otherise")
    singular_cohort = _reassign_transplants(singular_cohort)

    return singular_cohort