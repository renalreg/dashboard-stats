"""
################
LABELLER QUERIES
################

This module contains the raw queries which are used by the labellers to extract
ukrdc data. The scope of these functions should as far as possible be kept to
actually interacting with the database rather than processing and linking the
data.

"""

import zipfile
import shutil
from typing import List, Optional

import pandas as pd
import datetime as dt
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ukrdc_sqla.ukrdc import (
    LabOrder,
    ResultItem, 
    Address,
    PatientRecord,
    DialysisSession
)
from ukrdc_sqla.xmlarchive import Patient as XMLPatient, Assessment
from ukrdc_stats.utils.query import pid_ni_map

from urllib.request import urlretrieve
from pathlib import Path

ONS_ADDRESS_DATA_URL = (
    "https://www.arcgis.com/sharing/rest/content/items/"
    "3635ca7f69df4733af27caf86473ffa1/data"
)


def download_ons_address_data():
    """
    Download the ONS address data from the ArcGIS portal.
    """
    cache_dir = Path("cache/ons_postcode_data")
    cache_dir.mkdir(parents=True, exist_ok=True)

    zip_path = Path("cache/ons_data.zip")
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    urlretrieve(ONS_ADDRESS_DATA_URL, zip_path)
    
    with open(zip_path, "rb") as f:
        header = f.read(4)
    if header[:2] != b"PK":
        try:
            zip_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise ValueError(
            "ONS download did not return a zip file. "
            "Check ONS_ADDRESS_DATA_URL and network access."
        )

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall("cache/temp_extract")

    source_file = Path("cache/temp_extract/data/ONSPD_NOV_2025_UK.csv")
    if source_file.exists():
        shutil.copy2(source_file, cache_dir)

    shutil.rmtree("cache/temp_extract")
    zip_path.unlink(missing_ok=True)

    return


def query_ons_postcode_data() -> pd.DataFrame:

    cache_dir = Path("cache/ons_postcode_data")
    cache_dir.mkdir(parents=True, exist_ok=True)

    csv_path = cache_dir / "ONSPD_NOV_2025_UK.csv"
    if not csv_path.exists():
        download_ons_address_data()

    imd_data = pd.read_csv(
        csv_path,
        usecols=["pcd7", "imd20ind"],
        dtype={"pcd7": "string", "imd20ind": "int"},
        low_memory=False,
    ).drop_duplicates()

    imd_data["imddecile"] = pd.cut(
        imd_data["imd20ind"],
        bins=10,
        labels=[f"{i * 10}-{(i + 1) * 10}%" for i in range(10)],
        include_lowest=True,
    )

    return imd_data


def query_results(
    session: Session,
    pids: List[str],
    test_codes: Optional[List[str]] = None,
    chunk_size: int = 100,
    from_time: Optional[dt.datetime] = None,
    to_time: Optional[dt.datetime] = None,
) -> pd.DataFrame:
    """
    Extract test results for a cohort of patients using chunked queries
    to prevent database timeouts.
    """
    results = []

    for i in range(0, len(pids), chunk_size):
        chunk = pids[i : i + chunk_size]

        query = (
            select(
                LabOrder.pid,
                ResultItem.observationtime,
                ResultItem.serviceidcode,
                ResultItem.resultvalue,
                ResultItem.resultvalueunits,
            )
            .join(ResultItem, ResultItem.orderid == LabOrder.id)
            .where(LabOrder.pid.in_(chunk))
        )

        # Filter by specific test codes if provided (e.g. ['CREA', 'EGFR'])
        if test_codes:
            query = query.where(ResultItem.serviceidcode.in_(test_codes))

        if from_time:
            query = query.where(ResultItem.observationtime >= from_time)

        if to_time:
            query = query.where(ResultItem.observationtime <= to_time)

        chunk_data = session.execute(query).all()

        if chunk_data:
            results.extend(chunk_data)

    if not results:
        return pd.DataFrame(
            columns=[
                "pid",
                "observationtime",
                "serviceidcode",
                "resultvalue",
                "resultvalueunits",
            ]
        )

    return pd.DataFrame(results)


def query_postcodes(
    session: Session, pids: List[str], chunk_size: int = 100
) -> pd.DataFrame:
    """Extract postcodes for a cohort of patients.

    Returns a dataframe with one row per pid, selecting a single address by
    addressuse preference order: H, PST, NULL, TMP.
    """
    results = []

    for i in range(0, len(pids), chunk_size):
        chunk = pids[i : i + chunk_size]

        query = select(
            Address.pid,
            Address.postcode,
            Address.addressuse,
        ).where(Address.pid.in_(chunk))

        chunk_data = session.execute(query).all()
        if chunk_data:
            results.extend(chunk_data)
    df = pd.DataFrame(results)

    # Define preference order for addressuse

    if not results:
        return pd.DataFrame(columns=["pid", "postcode"])

    use_order = {"H": 1, "PST": 2, None: 3, "TMP": 4}
    df["use_priority"] = df["addressuse"].map(use_order).fillna(3)

    # Sort by pid and priority, then keep first occurrence per pid
    df = df.sort_values(["pid", "use_priority"]).groupby("pid", as_index=False).first()

    # Drop the priority column
    df = df.drop(columns=["use_priority", "addressuse"])

    return df

def query_careplanning(archieve_session: Session, facility_codes: List[str], prevalence_point: dt.datetime = None)->pd.DataFrame:
    """Extract care-planning assessments from the archive database. If a
    prevalence point is provided the most assessment prior to the prevelance 
    point is selected. 
    """
    
    assessments_query = (
        select(
            XMLPatient.nationalid.label("patientid"),
            XMLPatient.organization,
            XMLPatient.numbertype,
            XMLPatient.creation_date,
            Assessment.assessmentstart,
            Assessment.assessmentend,
            Assessment.assessmenttypecode,
            Assessment.assessmenttypecodestd,
            Assessment.assessmenttypecodedesc,
            func.trim(Assessment.assessmentoutcomecode).label("assessmentoutcomecode"),
            Assessment.assessmentoutcomecodestd,
            Assessment.assessmentoutcomecodedesc,
        )
        .join(
            Assessment,
            Assessment.patientid == XMLPatient.id,
        )
        .where(
            XMLPatient.sendingfacility.in_(facility_codes),
        )
    )
    
    if prevalence_point:
        assessments_query = assessments_query.where(
            Assessment.assessmentstart < prevalence_point
        )
        assessments_query = assessments_query.distinct(XMLPatient.nationalid, XMLPatient.organization)
        assessments_query = assessments_query.order_by(
            XMLPatient.nationalid,
            XMLPatient.organization,
            Assessment.assessmentstart.desc()
        )


    prevalent_assessments = archieve_session.execute(assessments_query).all()
    if not prevalent_assessments:
        prevalent_assessments_df = pd.DataFrame(columns=[
            "patientid", 
            "organization", 
            "numbertype", 
            "creation_date", 
            "assessmentstart", 
            "assessmentend", 
            "assessmenttypecode", 
            "assessmenttypecodestd", 
            "assessmenttypecodedesc", 
            "assessmentoutcomecode", 
            "assessmentoutcomecodestd", 
            "assessmentoutcomecodedesc"
        ])
    
    else:
        prevalent_assessments_df = pd.DataFrame(prevalent_assessments)
    
    return prevalent_assessments_df

def query_vascular_access(session, patient_list):
    
    query = (
        select(PatientRecord.pid, DialysisSession.procedure_time, DialysisSession.qhd20)
        .join(DialysisSession, DialysisSession.pid == PatientRecord.pid)
        .where(PatientRecord.pid.in_(patient_list))
        .order_by(PatientRecord.pid, DialysisSession.procedure_time)
    )

    vascular_access = pd.DataFrame(session.execute(query))
    if vascular_access.empty:
        vascular_access = pd.DataFrame(columns=["pid", "procedure_time", "qhd20"])
    
    return vascular_access