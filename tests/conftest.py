import tempfile
import json
from xml.etree.ElementInclude import include

import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from ukrdc_sqla.ukrdc import Base as UKRDC3Base

from ukrdc_sqla.ukrdc import PatientRecord


from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

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


def ukrdc_add_data(session: Session):
    """Adds fake data to the test UKRDC

    Args:
        session (Session): ukrdc test session.
    """

    class PatientRecordSchema(SQLAlchemyAutoSchema):
        class Meta:
            model = (PatientRecord,)
            include_fk = (True,)
            include_relationships = True

    dataschema = PatientRecordSchema()

    # loads serialised data for testing
    with open('test_data.json') as test_data_dictionary:
        test_data = dataschema.load(test_data_dictionary)
