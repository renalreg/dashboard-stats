import os
import glob
import pytest
import uuid

from sqlalchemy_utils import (
    drop_database,
    create_database
)

import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session 
from ukrdc_sqla.ukrdc import Base as UKRDC3Base

@pytest.fixture(scope="function")
def ukrdc3_session()->Session:
    """This fixture creates a new ukrdc database with unique name. It then
    populates with existing schema, updates with new features that cupid will
    require, and populates some but not all of the lookup tables.

    When control is handed  back to the function it will delete the database.

    Yields:
        Session: session on new ukrdc
    """

    # Generate a random string as part of the URL
    random_string = str(uuid.uuid4()).replace("-", "")
    db_name = f"test_ukrdc_{random_string}"
    url = f"postgresql://postgres:postgres@localhost:5432/{db_name}"

    create_database(url)
    engine = create_engine(url)
    UKRDC3Base.metadata.create_all(bind=engine)

    # load code mappings
    paths = glob.glob("scripts/codes/mappings/*.csv")
    for path in paths:
        data = pd.read_csv(path)
        data.to_sql("code_map", engine, if_exists="append", index=False)

    with sessionmaker(bind=engine)() as session:
        yield session

    # teardown database
    drop_database(url)

@pytest.fixture(scope="function")
def ukrdc3_real_db_session()->Session:
    """

    Returns:
        _type_: _description_

    Yields:
        _type_: _description_
    """
    env_file = '.env'
    
    # Check if .env file exists
    if not os.path.isfile(env_file):
        return None
    
    # Load the .env file
    load_dotenv(env_file)
    
    # Retrieve credentials
    ukrdc_host = os.getenv('UKRDC_HOST')
    ukrdc_port = os.getenv('UKRDC_PORT')
    ukrdc_user = os.getenv('UKRDC_USER')
    ukrdc_name = os.getenv('UKRDC_NAME')
    ukrdc_password = os.getenv('UKRDC_PASSWORD')

    if not all([ukrdc_host, ukrdc_port, ukrdc_user, ukrdc_name, ukrdc_password]):
        return None

    # Create the PostgreSQL connection URL
    database_url = f"postgresql://{ukrdc_user}:{ukrdc_password}@{ukrdc_host}:{ukrdc_port}/{ukrdc_name}"
    
    # Create SQLAlchemy engine and session
    engine = create_engine(database_url)
    with sessionmaker(bind=engine, autocommit=False)() as session: 
        yield session