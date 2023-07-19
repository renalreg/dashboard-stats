"""
Common utility functions useful in multiple statistics
"""

import datetime as dt
import pandas as pd
import fileinput
import redis

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ukrdc_sqla.ukrdc import CodeMap
from sqlalchemy.orm import Session
from sqlalchemy import and_, select
from dotenv import load_dotenv
import os

load_dotenv()

def cache_connection_from_env():
    # returns redis connection 
    redis_host = os.getenv('REDIS_CACHE_HOST')
    redis_port = os.getenv('REDIS_CACHE_PORT')
    redis_db = os.getenv('REDIS_CACHE_DB')

    return redis.Redis(host=redis_host, port = redis_port, db = redis_db)
    
def ukrdc_connection_from_env():
    
    # Get required variables for the connection string
    db_host = os.getenv('UKRDC_HOST')
    db_port = os.getenv('UKRDC_PORT')
    db_name = os.getenv('UKRDC_NAME')
    db_user = os.getenv('UKRDC_USER')
    db_password = os.getenv('UKRDC_PASSWORD')

    # Create the connection string
    ukrdc_connection_string = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    ukrdc3_sessionmaker = sessionmaker(
        autocommit=False, autoflush=False, bind=create_engine(ukrdc_connection_string)
    )

    return ukrdc3_sessionmaker()


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

    codes = pd.read_sql(query, session.bind)
    # print(codes.head())
    return dict(zip(codes.source_code, codes.destination_code))



def strip_whitespace(filepath: str):
    """Run to stop pylint complaining about trailing whitespace"""

    for line in fileinput.input(filepath, inplace=True):
        line = line.rstrip()
        if line:
            print(line)

