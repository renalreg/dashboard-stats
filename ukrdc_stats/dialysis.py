import datetime as dt
from typing import List


import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from ukrdc_sqla.ukrdc import Patient, PatientRecord, Treatment
from ukrdc_stats.utils import dob_cutoff_from_age


class DialysisStatsCalculator:
    """class to calcuate metrics associated with dialysis modalities"""

    def __init__(
        self,
        session: Session,
        facility: str,
        timewindow: List[dt.datetime],
        agewindow: List[int],
    ):
        """Dialysis stats object is produced

        Args:
            session (Session): _description_
            facility (str): _description_
            timewindow (list): _description_
            agewindow (list): _description_
        """

        self.session: Session = session
        self.facility: str = facility
        self.timewindow: List[dt.datetime] = timewindow
        self.dob_bracket: List[dt.datetime] = [
            dob_cutoff_from_age(self.timewindow[0], age) for age in reversed(agewindow)
        ]

        self.patient_cohort = self._extract_patient_cohort()
        self._incident_prevelent()

    def _extract_patient_cohort(self) -> pd.DataFrame:
        """

        Returns:
            pd.DataFrame: _description_
        """

        patient_query = (
            select(Patient, Treatment)  # type:ignore
            .join(Treatment, Treatment.pid == Patient.pid)  # type:ignore
            .join(PatientRecord, PatientRecord.pid == Patient.pid)  # type:ignore
            .where(
                and_(
                    # filter for facility
                    Treatment.health_care_facility_code == self.facility,
                    # ensure date of birth is within bracket
                    Patient.birth_time > self.dob_bracket[0],
                    Patient.birth_time < self.dob_bracket[1],
                    PatientRecord.sendingextract == "UKRDC",
                    # ensure patient is alive at beginning of time window
                    or_(
                        Patient.dead.is_(None), Patient.death_time > self.timewindow[0]
                    ),
                    # filter on dialysis modalities
                    or_(
                        Treatment.admit_reason_code == "1",
                        Treatment.admit_reason_code == "2",
                        Treatment.admit_reason_code == "3",
                        Treatment.admit_reason_code == "5",
                        Treatment.admit_reason_code == "11",
                        Treatment.admit_reason_code == "12",
                    ),
                )
            )
        )

        return pd.read_sql(patient_query, self.session.bind)

    def _incident_prevelent(self):

        return
