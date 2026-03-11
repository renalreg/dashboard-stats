import pandas as pd
from sqlalchemy.orm import Session
from ukrdc_stats.labellers.query import query_postcodes, query_ons_postcode_data


def imd(session: Session, patient_cohort: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the Index of Multiple Deprivation (IMD) for each patient.
    """

    # query patient postcodes
    postcodes = query_postcodes(session, patient_cohort["pid"].tolist())
    postcodes["postcode_norm"] = (
        postcodes["postcode"]
        .astype("string")
        .str.replace(" ", "", regex=False)
        .str.upper()
    )

    # query imd from ons
    imd_data = query_ons_postcode_data()
    imd_data["pcd7_norm"] = (
        imd_data["pcd7"].astype("string").str.replace(" ", "", regex=False).str.upper()
    )
    postcodes = postcodes.merge(
        imd_data,
        left_on="postcode_norm",
        right_on="pcd7_norm",
        how="left",
    )
    del imd_data
    postcodes.drop(columns=["postcode_norm", "pcd7_norm", "pcd7"], inplace=True)

    patient_cohort = patient_cohort.merge(
        postcodes[["pid", "imddecile"]],
        left_on="pid",
        right_on="pid",
        how="left",
    )

    return patient_cohort
