"""
Common utility functions useful in multiple statistics
"""

import datetime as dt
import pandas as pd
import fileinput
import warnings

from ukrdc_sqla.ukrdc import CodeMap, SatelliteMap
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import Optional, Dict, List


def age_from_dob(date: dt.date, dob: dt.date) -> int:
    """Returns the age on a given date

    Args:
        date (datetime): Date to calculate age or time period from.
        dob (datetime): Date to calculate age or time period at.

    Returns:
        int: age or period in years
    """
    years_old: int

    # calculates age by common definition
    years_old = date.year - dob.year
    if (dob.month == 2) & (dob.day == 29):
        # handles case where birthday is on leap day
        year_birthday = dt.datetime(date.year, dob.month, dob.day - 1)
    else:
        year_birthday = dt.datetime(date.year, dob.month, dob.day)

    if year_birthday > date:
        years_old -= 1

    return years_old


def age_from_dob_exact(date: dt.date, dob: dt.date) -> float:
    """Generates an exact dob as decimal

    Args:
        date (dt.date): Date to calculate age or time period from.
        dob (dt.date): Date to calculate age or time period at.

    Returns:
        float: age
    """

    return (date - dob).days / 365.25


def dob_cutoff_from_age(date: dt.datetime, age: int) -> dt.datetime:
    """returns a date a fixed number of years before give date

    Args:
        date (dt.date): date to calculate from
        age (int): number of years before date

    Returns:
        dt.date: date a set number of years ago
    """

    return date - dt.timedelta(days=age * 365.25)


def map_codes(source_std: str, destination_std: str, session: Session) -> dict:
    query = select(CodeMap.source_code, CodeMap.destination_code).where(
        and_(
            CodeMap.source_coding_standard == source_std,
            CodeMap.destination_coding_standard == destination_std,
        )
    )

    codes = pd.DataFrame(session.execute(query))

    return dict(zip(codes.source_code, codes.destination_code))


def strip_whitespace(filepath: str):
    """Run to stop pylint complaining about trailing whitespace"""

    for line in fileinput.input(filepath, inplace=True):
        line = line.rstrip()
        if line:
            print(line)


def _mapped_key(key: str) -> str:
    """Tiny convenience function to return a common mapped column name

    Args:
        key (str): Column to map

    Returns:
        str: Mapped column name
    """
    return f"{key}_mapped"


def _calculate_base_patient_histogram(
    cohort: pd.DataFrame, group: str, code_map: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """Extract a histogram of the patient cohort, grouped by the given column

    Args:
        cohort (pd.DataFrame): Patient cohort
        group (str): Column to group by

    Raises:
        NoCohortError: If the patient cohort is empty

    Returns:
        pd.DataFrame: Histogram dataframe of the patient cohort
    """

    if code_map:
        mapped_column = _mapped_key(group)
        cohort[mapped_column] = cohort[group].map(code_map)

        histogram = (
            cohort[["ukrdcid", mapped_column]]
            .drop_duplicates()
            .groupby([mapped_column])
            .count()
            .reset_index()
        )

    else:
        histogram = (
            cohort[["ukrdcid", group]]
            .drop_duplicates()
            .groupby([group])
            .count()
            .reset_index()
        )

    return histogram.rename(columns={"ukrdcid": "Count"})


def _mapped_if_exists(df: pd.DataFrame, column: str) -> pd.Series:
    """
    Convenience function to return the mapped column if it exists,
    otherwise return the original column

    Args:
        df (pd.DataFrame): Input dataframe
        column (str): Column to return

    Returns:
        pd.Series: Mapped column if it exists, otherwise the original column
    """
    mapped_column: str = _mapped_key(column)
    if mapped_column in df.columns:
        return df[mapped_column]
    else:
        warnings.warn(
            f"Column {mapped_column} does not exist in dataframe, returning {column} instead"
        )
        return df[column]


def _get_satellite_list(facility_code: str, session: Session) -> List[str]:
    """
    Get the list of satellites for the facility.
    """
    query = select(SatelliteMap.satellite_code).where(
        SatelliteMap.main_unit_code == facility_code
    )
    return session.execute(query).scalars().all()
