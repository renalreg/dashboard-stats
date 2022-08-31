import tempfile
import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ukrdc_sqla.ukrdc import Base as UKRDC3Base

# Using the factory to create a postgresql instance
socket_dir = tempfile.TemporaryDirectory()
postgresql_my_proc = factories.postgresql_proc(port=None, unixsocketdir=socket_dir.name)
postgresql_my = factories.postgresql("postgresql_my_proc")


@pytest.fixture(scope="function")
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

    # Returnt the test session
    return ukrdc_sessionmaker()
