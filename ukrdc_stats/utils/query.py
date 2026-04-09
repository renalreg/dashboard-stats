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
    pids = pd.DataFrame(session.execute(query))

    if pids.empty:
        raise EmptyCohortError

    return pids