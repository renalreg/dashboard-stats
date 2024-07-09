"""
Common utility functions useful in multiple statistics
"""

import datetime as dt
import pandas as pd
import fileinput

from ukrdc_sqla.ukrdc import CodeMap
from sqlalchemy.orm import Session
from sqlalchemy import select, and_


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

    codes = pd.read_sql(query, session.bind)  # type : ignore
    # print(codes.head())
    return dict(zip(codes.source_code, codes.destination_code))


def strip_whitespace(filepath: str):
    """Run to stop pylint complaining about trailing whitespace"""

    for line in fileinput.input(filepath, inplace=True):
        line = line.rstrip()
        if line:
            print(line)
