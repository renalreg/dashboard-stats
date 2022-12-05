"""
Patient cohort dialysis stats calculator
"""

import datetime as dt

from typing import Literal, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import DialysisSession, Patient, PatientRecord, Treatment

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError
from pydantic import Field


from ..models.generic_2d import (
    AxisLabels2d,
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
)

from ..models.networks import LabelledNetwork, NetworkMetaData, Nodes, Connections
from ..descriptions import dialysis_descriptions
from ..models.base import JSONModel


class DialysisMetadata(JSONModel):
    population: Optional[int] = Field(
        None,
        description="Number of patients in the cohort for dialysis stats calculation",
    )
    from_time: dt.datetime = Field(
        ..., description="Start time of dialysis stats calculations"
    )
    to_time: dt.datetime = Field(
        ..., description="End time of dialysis stats calculations"
    )


class DialysisStats(JSONModel):
    """
    Container class for all the dialysis stats
    """

    all_patients_home_therapies: LabelledNetwork = Field(
        ...,
        description="statistical breakdown of therapy types for all patients in cohort",
    )
    incident_home_therapies: LabelledNetwork = Field(
        ...,
        description="statistical breakdown of therapy types for incident patients in cohort",
    )
    prevalent_home_therapies: LabelledNetwork = Field(
        ...,
        description="statistical breakdown of therapy types for prevalent patients in cohort",
    )
    incentre_dialysis_frequency: Labelled2d = Field(
        ...,
        description="per week frequency of dialysis for all in-centre dialysis patients",
    )
    incident_initial_access: Labelled2d = Field(
        ...,
        description="vascular access of incident dialysis patients on their first session",
    )
    metadata: DialysisMetadata


def _calculate_frequency(
    from_time: dt.datetime, to_time: dt.datetime, no_of_events: int
):
    """calculates the frequency in per week units of events in a given timewindow

    Args:
        from_time (dt.datetime): start of window
        to_time (dt.datetime): end of window
        no_of_proceedures (int): no of things/events/proceedures which have occured

    Returns:
        _type_: frequency of events
    """
    delta_t = (to_time - from_time).days

    if delta_t > 0.0:
        return 7.0 * no_of_events / delta_t
    # else:
    # TODO: add proper error handling to this
    #    print("Time window is not positive and non-zero")

    return None


class DialysisStatsCalculator(AbstractFacilityStatsCalculator):
    """class to calcuate metrics associated with dialysis modalities"""

    def __init__(
        self,
        session: Session,
        facility: str,
        from_time: dt.datetime,
        to_time: dt.datetime,
    ):
        super().__init__(session, facility)

        # Create a precisely 2 element time window tuple
        self.time_window: Tuple[dt.datetime, dt.datetime] = (from_time, to_time)

    def _extract_base_patient_cohort(self) -> pd.DataFrame:
        """Extract a base patient cohort dataframe from the database

        Returns:
            pd.DataFrame: Patient cohort dataframe
        """

        cohort_definition = (
            select(
                PatientRecord.ukrdcid,
                PatientRecord.pid,
            )
            .join(Treatment, Treatment.pid == PatientRecord.pid)
            .where(
                and_(
                    PatientRecord.sendingextract == "UKRDC",
                    Treatment.health_care_facility_code == self.facility,
                    Treatment.from_time < self.time_window[1],
                    or_(
                        Treatment.to_time > self.time_window[0],
                        Treatment.to_time.is_(None),
                    ),
                    Treatment.admit_reason_code.in_(["1", "2", "3", "5", "11", "12"]),
                )
            )
            .group_by(PatientRecord.pid, PatientRecord.ukrdcid)
        ).subquery()

        # join all treatments by members of the cohort
        patient_query = (
            select(
                cohort_definition,
                Treatment.admit_reason_code,
                Treatment.qbl05,
                Treatment.hdp04,
                Treatment.from_time,
                Treatment.to_time,
                Patient.death_time,
            )
            .join(Treatment, Treatment.pid == cohort_definition.c.pid)
            .join(Patient, Patient.pid == Treatment.pid)
            .where(
                and_(
                    Treatment.from_time < self.time_window[1],
                    or_(
                        Treatment.to_time > self.time_window[0],
                        Treatment.to_time.is_(None),
                    ),
                )
            )
        )

        return pd.read_sql(patient_query, self.session.bind)

    def extract_patient_cohort(self):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        """
        self._patient_cohort = self._extract_base_patient_cohort()

    def start_groupings(self):

        print(
            self._patient_cohort[
                self._patient_cohort.admitreasoncode.isin(["20", "29", "78"])
                & (self._patient_cohort.fromtime < self.time_window[0])
            ].head()
        )

        # patients on transplant modalities
        """
        self._patient_cohort["start_groupings"][
            (self._patient_cohort.fromtime < self.time_window[0])
            & self._patient_cohort.admitreasoncode.isin(["29", "78", "20"])
        ] = "Tx"
        """

    def extract_stats(self) -> DialysisStats:
        """Extract all stats for the dialysis module

        Returns:
            DialysisStats: Dialysis statistics object
        """
        # If we don't already have a patient cohort, extract one

        if self._patient_cohort is None:
            self.extract_patient_cohort()

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # TODO: Do we want metadata like population size here?
        #       See DemographicStatsCalculator.extract_stats
        return DialysisStats(
            all_patients_home_therapies="",
            incident_home_therapies="",
            prevalent_home_therapies="",
            incentre_dialysis_frequency="",
            incident_initial_access="",
        )
