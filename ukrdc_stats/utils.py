"""
Common utility functions useful in multiple statistics
"""

import datetime as dt
from ukrdc_sqla.ukrdc import Code
import pandas as pd
import fileinput
import warnings

from ukrdc_sqla.ukrdc import CodeMap, SatelliteMap
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import Optional, Dict, List
from pathlib import Path


def egfr(
    scr: float,
    scr_unit: str,
    scr_date: dt.datetime,
    dob: dt.datetime,
    sex: int = 1,
    ethnicity: Optional[str] = None,
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

    codes = pd.DataFrame(session.execute(query))

    return dict(zip(codes.source_code, codes.destination_code))


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

path_to_codes = Path.cwd()/"scripts"/"codes"/"mappings"
df = pd.read_csv(path_to_codes/"unit_full_names.csv")
facility_names = dict(zip(df['code'], df['name']))

df = pd.read_csv(path_to_codes/"main_unit_short_names.csv")
short_names = dict(zip(df['code'], df['short']))

df = pd.read_csv(path_to_codes/"main_unit_region.csv")
region_map = dict(zip(df['code'], df['region']))

def check_headcounts(cohort: pd.DataFrame, groupby_attributes: list[str] = []):
    """Used in the scripts to ensure headcounts remain consistent and patients
    aren't being dropped

    Args:
        cohort (pd.DataFrame): dataframe with coumns group_byattributes + value
        groupby_attributes (_type_, optional): columns to label data e.g centre

    Raises:
        Warning: _description_
    """

    if not groupby_attributes:
        groupby_attributes = ["satellite_code", "centre_code", "variable2"]

    # remove paeds to keep things simple
    if "adultpaed" in cohort.columns:
        cohort = cohort[cohort["adultpaed"] == "Adult"]

    # aggregate over specified columns
    head_count = (
        cohort.groupby(groupby_attributes)
        .sum(numeric_only=True)
        .reset_index()[groupby_attributes + ["value"]]
    )

    # intialise some bits for use later
    label_columns = groupby_attributes.copy()
    if "variable2" in label_columns:
        label_columns.remove("variable2")

    previous_labels = None
    previous_value = None
    msg = None

    # cross check rows for consistency
    for _, row in head_count.iterrows():
        labels = row[label_columns].to_list()
        value = row["value"]

        if labels == previous_labels:
            if value != previous_value:
                msg = "Headcount id variable across categories\n"
                mask = (
                    head_count[label_columns] == pd.Series(labels, index=label_columns)
                ).all(axis=1)
                msg += head_count[mask].to_string(index=False) + "\n"
        else:
            previous_labels = labels
            previous_value = value

    if msg:
        raise Warning(msg)

    return
