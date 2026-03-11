import os
import zipfile
import shutil
from typing import List, Optional

import pandas as pd
import datetime as dt
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import LabOrder, ResultItem, Address

from urllib.request import urlretrieve
from pathlib import Path

ONS_ADDRESS_DATA_URL = (
    "https://www.arcgis.com/sharing/rest/content/items/"
    "3635ca7f69df4733af27caf86473ffa1/data"
)

def download_ons_address_data():
    cache_dir = Path("cache/ons_postcode_data")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    zip_path = Path("cache/ons_data.zip")
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    urlretrieve(ONS_ADDRESS_DATA_URL, zip_path)
    
    # ArcGIS will happily serve HTML when the URL is wrong or rate-limited.
    # Fail fast rather than caching junk.
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
    "This currently requires lots of memory so should be revisited at some point"
    
    cache_dir = Path("cache/ons_postcode_data")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = cache_dir / "ONSPD_NOV_2025_UK.csv"
    if not csv_path.exists():
        download_ons_address_data()
    imd_data = pd.read_csv(csv_path)[["pcd7", "imd20ind"]].drop_duplicates()
    
    imd_data["imddecile"] = pd.cut(
        imd_data["imd20ind"], 
        bins=10, 
        labels=[f"{i*10}-{(i+1)*10}%" for i in range(10)], 
        include_lowest=True
    )
    
    return imd_data
 

def query_results(
    session: Session, 
    pids: List[str], 
    test_codes: Optional[List[str]] = None,
    chunk_size: int = 100,
    from_time: Optional[dt.datetime] = None,
    to_time: Optional[dt.datetime] = None
) -> pd.DataFrame:
    """
    Extract test results for a cohort of patients using chunked queries 
    to prevent database timeouts.
    """
    results = []
    
    for i in range(0, len(pids), chunk_size):
        chunk = pids[i:i + chunk_size]
        
        query = (
            select(
                LabOrder.pid,
                ResultItem.observationtime,
                ResultItem.serviceidcode,
                ResultItem.resultvalue,
                ResultItem.resultvalueunits
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
        return pd.DataFrame(columns=['pid', 'observationtime', 'serviceidcode', 'resultvalue', 'resultvalueunits'])
        
    return pd.DataFrame(results)


def query_postcodes(session: Session, pids: List[str], chunk_size: int = 100) -> pd.DataFrame:
    """Extract postcodes for a cohort of patients.

    Returns a dataframe with one row per pid, selecting a single address by
    addressuse preference order: H, PST, NULL, TMP.
    """
    results = []
    
    for i in range(0, len(pids), chunk_size):
        chunk = pids[i : i + chunk_size]

        query = (
            select(
                Address.pid,
                Address.postcode,
                Address.addressuse,
            )
            .where(Address.pid.in_(chunk))
        )

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