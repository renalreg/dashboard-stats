"""
Common utility functions useful in multiple statistics
"""

from pathlib import Path
from typing import List
import datetime as dt
import pandas as pd


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
    years_old = date.year - dob.year - 1
    try:
        year_birthday = dt.datetime(date.year, dob.month, dob.day)
    except ValueError:
        # exemption triggered for people with birthday on leap year if not a leap year
        year_birthday = dt.datetime(date.year, dob.month, dob.day - 1)

    if year_birthday <= date:
        years_old += 1

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


def nhs_data_lookup(item_name: str, code: List[str]) -> List[str]:
    """
    Loads codes used by nhs data directory
        https://nhs-digital.citizenspace.com/data-dictionary/nhs-dmds-reference-da/

    TODO:
        - unit test to check file is up to date?
        - pydantic output

    Args:
        item_name (str): name of item to be loaded (e.g Person_Gender_Code_Current)
        code (list(str)): codes to return discriptions

    Returns:
        list(str): return descriptions
    """

    code_file = "CDS V6-2 Type 020 - Outpatient Commissioning Data Set - Reference Data - V1.csv"

    codes = pd.read_csv(
        Path(__file__).parent.joinpath(code_file), encoding="ISO-8859-1"
    )

    codes_desc = codes[
        (codes.Item_Name == item_name) & (codes.Code.isin(code))
    ].Code_Short_Description.values

    return [str(desc) for desc in codes_desc]
