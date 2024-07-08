import tempfile
import glob
import pytest
import uuid

from sqlalchemy_utils import (
    database_exists,
    drop_database,
    create_database
)

import pandas as pd
from pytest_postgresql import factories
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ukrdc_sqla.ukrdc import Base as UKRDC3Base

@pytest.fixture(scope="function")
def ukrdc3_session():
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