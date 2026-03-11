"""
Common utility functions useful in multiple statistics
"""

import datetime as dt
from ukrdc_sqla.ukrdc import Code
import pandas as pd
import fileinput
import warnings

from ukrdc_sqla.ukrdc import CodeMap
from ukrdc_stats.exceptions import MissingColumnError
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import Optional, Dict


def egfr(
    scr: float,
    scr_unit: str,
    scr_date: dt.datetime,
    dob: dt.datetime,
    sex: int = 1,
) -> Optional[int]:
    """Function for calculating the egfr based on the equation found here:
    http://nephron.com/epi_equation

    Args:
        scr (int): serum creatinine level
        scr_unit (str): unit of serum creatinine
        scr_date (dt.datetime): date of serum creatinine measurement
        dob (dt.datetime): date of birth
        sex (int, optional): sex of patient. Defaults to 1 (male).
        ethnicity (Optional[str], optional): ethnicity of patient. Defaults to None.

    Returns:
        Optional[int]: estimated glomerular filtration rate
    """

    if pd.isna(scr) or pd.isna(scr_date):
        return

    age = age_from_dob_exact(scr_date, dob)

    if age < 18:
        return

    # only accept creatinines with accepted units
    if scr_unit == "umol/L":
        scr = scr / 88.4
    elif scr_unit == "mmol/L":
        scr = scr / (10 * 88.4)
    elif scr_unit == "g/L":
        scr = 100.0 * scr
    elif scr_unit == "mg/dL":
        pass
    else:
        return

    if sex == "2":
        kappa = 0.7
        alpha = -0.329
        multiplier = 1.018
    else:
        kappa = 0.9
        alpha = -0.411
        multiplier = 1.0

    scr_frac = scr / kappa
    if scr_frac > 1:
        multiplier = multiplier * (scr_frac**-1.209)
    else:
        multiplier = multiplier * (scr_frac**alpha)

    egfr = round(141 * multiplier * (0.993**age))

    return egfr


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
    """Use the code map table to return a code mapping set from the ukrdc as a
    dictionary.

    Args:
        source_std (str): _description_
        destination_std (str): _description_
        session (Session): _description_

    Returns:
        dict: _description_
    """

    query = select(CodeMap.source_code, CodeMap.destination_code).where(
        and_(
            CodeMap.source_coding_standard == source_std,
            CodeMap.destination_coding_standard == destination_std,
        )
    )

    codes = {row.source_code: row.destination_code for row in session.execute(query)}
    if not codes:
        raise ValueError(
            f"No codes found for source coding standard '{source_std}' and destination coding standard '{destination_std}'"
        )

    return codes


def lookup_codes(
    coding_standard: str, attribute: str, session: Session
) -> Dict[str, str]:
    """Get a code set from the ukrdc lookup and return some attribute from it
    (most likely the description)

    Args:
        coding_standard (str): The coding standard to lookup
        attribute (str): The attribute to return (e.g., 'description')
        session (Session): SQLAlchemy database session

    Returns:
        Dict[str, str]: Dictionary mapping code values to the requested attribute
    """
    # Build and execute query properly
    query = select(Code).where(Code.coding_standard == coding_standard)
    result = session.execute(query).scalars().all()

    # Handle empty results
    if not result:
        warnings.warn(f"No codes found for coding standard '{coding_standard}'")
        return {}

    # Convert to dictionary directly from ORM objects
    return {code.code: getattr(code, attribute, None) for code in result}


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


def row_completeness(row: pd.Series, groupby_attributes: list[str]) -> int:
    """Calculate completeness based on specified groupby attributes"""
    return row[groupby_attributes].notnull().sum()


def aggregate_data(
    cohort_wide: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Function generates and aggregated dataframe in long format with
    headcounts (ukrdcid) split by the specified columns. The remaining columns
    will be rolled into the attribute (column name) and variable (column value)
    columns.

    Args:
        cohort_wide (pd.DataFrame): dataframe containing patient data
        columns (list[str]): _description_

    Returns:
        pd.DataFrame: _description_
    """

    if "ukrdcid" not in cohort_wide.columns:
        raise MissingColumnError("ukrdcid not found in cohort_wide")

    if not all(col in cohort_wide.columns for col in columns):
        raise MissingColumnError(
            "input variable cohort wide does not contain all the specified columns"
        )

    columns.insert(0, "ukrdcid")
    value_columns = [col for col in cohort_wide.columns if col not in columns]

    # transform dataframe into long form and count heads
    cohort_long = cohort_wide.melt(
        id_vars=columns,
        value_vars=value_columns,
        var_name="attribute",
        value_name="variable",
    )
    cohort_long = (
        cohort_long.groupby(
            ["attribute", "variable"] + [col for col in columns if col != "ukrdcid"],
            dropna=False,
        )
        .agg({"ukrdcid": "nunique"})
        .reset_index()
    )

    cohort_long = cohort_long.rename(columns={"ukrdcid": "count"})

    return cohort_long


VASCULAR_MAPPING = {
    "AVF": "AVF/AVG",
    "AVFUO": "AVF/AVG",
    "AVG": "AVF/AVG",
    "TLN": "TL",
    "NLN": "NTL",
    "HER": "AVF/AVG",
}

# NHS digital gender map
GENDER_GROUP_MAP = {"1": "Male", "2": "Female", "9": "Indeterminate", "X": "Unknown"}


AGE_BINS = {
    "labels": ["<18", "18-34", "35-54", "55-74", ">=75"],
    "bins": [0, 18, 35, 55, 75, 150],
}
