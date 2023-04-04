import tempfile
import glob
import pytest

import pandas as pd
from pytest_postgresql import factories
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ukrdc_sqla.ukrdc import Base as UKRDC3Base


# Using the factory to create a postgresql instance
socket_dir = tempfile.TemporaryDirectory()
postgresql_my_proc = factories.postgresql_proc(port=None, unixsocketdir=socket_dir.name)
postgresql_my = factories.postgresql("postgresql_my_proc")

# if you have postgres runnin you can uncomment this line
postgresql_my = factories.postgresql('postgresql_noproc')

# and run pytest with this line
# pytest --postgresql-user postgres --postgresql-password postgres


@pytest.fixture()
def ukrdc3_session(postgresql_my):
    """
    Create a new function-scoped in-memory UKRDC3 database and return the session class
    """

    def dbcreator():
        return postgresql_my.cursor().connection

    engine = create_engine("postgresql+psycopg2://", creator=dbcreator)
    ukrdc_sessionmaker = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    # Create the database schema, tables etc
    UKRDC3Base.metadata.create_all(bind=engine)

    # load code mappings
    paths = glob.glob("scripts/codes/mappings/*.csv")
    for path in paths:
        data = pd.read_csv(path)
        data.to_sql("code_map", engine, if_exists="append", index=False)

    # assert 1 == 2
    # Returnt the test session
    return ukrdc_sessionmaker()
