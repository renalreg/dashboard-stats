from ukrdc_sqla.ukrdc import (
    PatientRecord,
    PatientNumber,
)
from sqlalchemy import select
from sqlalchemy.orm import Session
import pandas as pd
from ukrdc_stats.exceptions import EmptyCohortError


def pid_ni_map(session: Session, facilities: list[str]) -> pd.DataFrame:
    """
    Function returns a mapping of patient ids to national ids for a given facility.
    """
    query = (
        select(PatientNumber.pid, PatientNumber.patientid, PatientNumber.organization)
        .distinct(
            PatientNumber.pid, PatientNumber.patientid, PatientNumber.organization
        )
        .join(PatientRecord, PatientNumber.pid == PatientRecord.pid)
        .where(PatientRecord.sendingfacility.in_(facilities))
    )
    pids = pd.DataFrame(session.execute(query).all())

    if pids.empty:
        raise EmptyCohortError

    return pids


def sendingfacility_main_unit_map(session: Session) -> pd.DataFrame:
    """
    Function returns a mapping of sending facility codes to main unit codes.
    """
    query = (
        select(PatientRecord.sendingfacility, PatientRecord.mainunit)
        .distinct(PatientRecord.sendingfacility, PatientRecord.mainunit)
    )
    sendingfacilities = pd.DataFrame(session.execute(query).all())

    if sendingfacilities.empty:
        raise EmptyCohortError

    return sendingfacilities