"""
Patient cohort dialysis stats calculator
"""

import datetime as dt
from typing import Literal, Optional, Tuple, Union

import numpy as np
import pandas as pd
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import (
    DialysisSession,
    Patient,
    PatientRecord,
    Treatment,
)

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError

from ..models.generic_2d import (
    AxisLabels2d,
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
)

from ..models.networks import LabelledNetwork, NetworkMetaData, Nodes, Vertices


class DialysisMetadata(BaseModel):
    population: Optional[int] = None
    from_time: dt.datetime
    to_time: dt.datetime


class DialysisStats(BaseModel):
    all_patients_home_therapies: LabelledNetwork
    incident_home_therapies: LabelledNetwork
    prevalent_home_therapies: LabelledNetwork
    incentre_dialysis_frequency: Labelled2d
    incident_initial_access: Labelled2d
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

        patient_query = (
            select(
                PatientRecord.ukrdcid,
                Patient.pid,
                Treatment.admit_reason_code,
                Treatment.qbl05,
                Treatment.hdp04,
                Treatment.from_time,
                Treatment.to_time,
                Patient.death_time,
                Patient.dead,
            )  # type:ignore
            .join(Treatment, Treatment.pid == Patient.pid)  # type:ignore
            .join(PatientRecord, PatientRecord.pid == Patient.pid)  # type:ignore
            .where(
                and_(
                    # filter for facility
                    Treatment.health_care_facility_code == self.facility,
                    PatientRecord.sendingextract == "UKRDC",
                    # ensure patient is alive at beginning of time window
                    or_(
                        Patient.dead.is_(None), Patient.death_time > self.time_window[0]
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

    def _extract_incident_prevalent(self, base_cohort: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a base cohort from _extract_base_patient_cohort and extracts the incident and prevalent patients.

        This is currently a draft version and probably needs careful reviewing.

        Args:
            base_cohort (pd.DataFrame): Base cohort from output of _extract_base_patient_cohort

        Returns:
            pd.DataFrame: Patient cohort dataframe
        """

        # If patients are alive and have not been discharged count them as prevalent
        base_cohort["prevalent"] = (
            pd.isnull(base_cohort.deathtime)
            | (base_cohort.deathtime > self.time_window[1])
        ) & ((base_cohort.totime > self.time_window[1]) | pd.isnull(base_cohort.totime))
        base_cohort.prevalent.fillna(False)

        # Get a list of patients to check for incidence status. All incident patients start within the timewindow.
        incident_ids = base_cohort[["ukrdcid"]][
            base_cohort.fromtime > self.time_window[0]
        ].drop_duplicates()

        # Run query to test if they have appeared as hd, pd, or Tx prior to beginning of window these will be discounted
        not_incident_ids_query = (
            select(PatientRecord.ukrdcid)
            .join(Treatment)
            .where(
                and_(
                    Treatment.admit_reason_code.in_(
                        ["1", "2", "3", "5", "11", "12", "20", "29", "78"]
                    ),
                    Treatment.from_time < self.time_window[0],
                    PatientRecord.ukrdcid.in_(incident_ids.ukrdcid.to_numpy()),
                )
            )
        )
        not_incident_ids = self.session.execute(not_incident_ids_query).all()

        # label patients identified in incident_ids who do not appear in previous group as incident
        incident_ids["incident"] = ~incident_ids.ukrdcid.isin(
            [id[0] for id in not_incident_ids]
        )

        # merge into patient cohort and replace NaN with false
        merged = pd.merge(base_cohort, incident_ids, how="left", on="ukrdcid")
        merged.incident = merged.incident.fillna(False)

        return merged

    def _calculate_therapy_types(
        self, scope: Literal["all", "incident", "prevalent"]
    ) -> Tuple[Nodes, Vertices]:
        """
        Breakdown of dialysis patients on home and in-centre therapies.
        The information is returned using pydantic classes designed handle
        networks (this is essentially what a sankey plot is)

        Args:
            Scope: allows stats to be calculated for incident, prevalent or all patients

        Returns:
            Nodes, Vertices: pydantic classes containing calculated data
        """
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # Filter patient cohort based on incident, prevalent or all
        patient_cohort: Union[pd.DataFrame, pd.Series]
        if scope == "all":
            patient_cohort = self._patient_cohort
        elif scope == "incident":
            patient_cohort = self._patient_cohort[self._patient_cohort.incident]
        elif scope == "prevalent":
            patient_cohort = self._patient_cohort[self._patient_cohort.prevalent]
        else:
            raise ValueError("Invalid scope")

        # filter patients in cohort with Haemodialysis modalities who are receiving therapies in hospital
        hosp_hd = len(
            patient_cohort[
                patient_cohort.admitreasoncode.isin(["1", "2", "3", "5"])
                & (patient_cohort.qbl05 == "HOSP")
            ]["ukrdcid"].drop_duplicates()
        )

        # filter "" on home therapies
        home_hd = len(
            patient_cohort[
                patient_cohort.admitreasoncode.isin(["1", "2", "3", "5"])
                & (patient_cohort.qbl05 == "HOME")
            ]["ukrdcid"].drop_duplicates()
        )

        # filter "" where database does not provide information
        na_hd = len(
            patient_cohort[
                patient_cohort.admitreasoncode.isin(["1", "2", "3", "5"])
                & patient_cohort.qbl05.isnull()
            ]["ukrdcid"].drop_duplicates()
        )

        # patients on peritoneal dialysis which presumably all happens at home
        home_pd = len(
            patient_cohort[patient_cohort.admitreasoncode.isin(["11", "12"])][
                "ukrdcid"
            ].drop_duplicates()
        )

        # assemble calculated numbers into the pydantic data structures used by the api
        nodes = Nodes(
            node_labels=[
                "Haemodialysis",
                "Peritoneal dialysis",
                "Home therapies",
                "In-centre therapies",
                "Incomplete/Not given",
            ]
        )

        vertices = Vertices(
            source=["0", "0", "0", "1"],
            target=["2", "3", "4", "2"],
            value=[str(home_hd), str(hosp_hd), str(na_hd), str(home_pd)],
        )

        return nodes, vertices

    def _calculate_dialysis_frequency(self):
        """
        Calculate the frequency with which dialysis occurs
        """
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # get list of hd patients
        patient_list = self._patient_cohort[
            (self._patient_cohort.admitreasoncode.isin(["1", "2", "3", "5"]))
            & (self._patient_cohort.qbl05 == "HOSP")
        ].ukrdcid.drop_duplicates()

        # get number of dialysis sessions per patient and the date of the first and last one
        query = (
            select(
                PatientRecord.ukrdcid,
                func.min(DialysisSession.procedure_time).label("fromtime"),
                func.max(DialysisSession.procedure_time).label("totime"),
                func.count(DialysisSession.procedure_type_code).label("sessioncount"),
            )
            .join(DialysisSession, DialysisSession.pid == PatientRecord.pid)
            .where(
                and_(
                    PatientRecord.ukrdcid.in_(patient_list),
                    DialysisSession.procedure_type_code == "302497006",  # filter for hd
                    DialysisSession.procedure_time > self.time_window[0],
                    DialysisSession.procedure_time < self.time_window[1],
                )
            )
            .group_by(PatientRecord.ukrdcid)
        )

        session_data = pd.read_sql(query, self.session.bind)

        # calculate frequency of dialysis
        session_data["freq"] = session_data.apply(
            lambda row: _calculate_frequency(
                row["fromtime"], row["totime"], row["sessioncount"]
            ),
            axis=1,
            result_type="reduce",
        )

        # turn into  histogram
        nbins = 15
        bins = np.linspace(0, 7, nbins)
        labels = [f"{bins[i-1]}- {bins[i]}" for i in range(1, nbins)]
        hist = pd.cut(session_data.freq, bins=bins, labels=labels).value_counts(
            sort=False
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="In-Centre Dialysis Frequency",
                summary="",
                description="",
                axis_titles=AxisLabels2d(
                    x="Frequency (days per week)", y="No. of Patients"
                ),
            ),
            data=Labelled2dData(
                x=list(hist.keys()), y=[int(value) for value in hist.values]
            ),
        )

    def _calculate_access_incident(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        window = (
            select(
                PatientRecord.ukrdcid,
                DialysisSession.procedure_time,
                DialysisSession.qhd20,
                func.rank()
                .over(
                    order_by=DialysisSession.procedure_time,
                    partition_by=PatientRecord.ukrdcid,
                )
                .label("rnk"),
            )
            .join(DialysisSession, DialysisSession.pid == PatientRecord.pid)
            .where(
                PatientRecord.ukrdcid.in_(
                    # pylint: disable=singleton-comparison
                    self._patient_cohort[self._patient_cohort.incident == True].ukrdcid
                )
            )
        ).subquery()

        initial_access_query = (
            select(window.c.qhd20, func.count(window.c.ukrdcid).label("no"))
            .group_by(window.c.qhd20)
            .where(window.c.rnk == 1)
        )

        initial_access_data = pd.read_sql(initial_access_query, self.session.bind)

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Initial Vascular Access of Incident Patients",
                summary="",
                description="",
                axis_titles=AxisLabels2d(x="Line Type", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=list(initial_access_data.qhd20), y=list(initial_access_data.no)
            ),
        )

    def _calculate_all_home_therapies(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        all_patients_nodes, all_patients_vertices = self._calculate_therapy_types("all")

        return LabelledNetwork(
            metadata=NetworkMetaData(
                title="Proportion of all Dialysis Patients on Home Therapies",
                summary="",
                description="",
            ),
            node=all_patients_nodes,
            link=all_patients_vertices,
        )

    def _calculate_incident_home_therapies(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        incident_nodes, incident_vertices = self._calculate_therapy_types("incident")

        return LabelledNetwork(
            metadata=NetworkMetaData(
                title="Proportion of Incident Patients on Home Therapies",
                summary="",
                description="",
            ),
            node=incident_nodes,
            link=incident_vertices,
        )

    def _calculate_prevalent_home_therapies(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        prevalent_nodes, prevalent_vertices = self._calculate_therapy_types("prevalent")

        return LabelledNetwork(
            metadata=NetworkMetaData(
                title="Proportion of Prevalent Patients on Home Therapies",
                summary="",
                description="",
            ),
            node=prevalent_nodes,
            link=prevalent_vertices,
        )

    def extract_patient_cohort(self):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        """
        self._patient_cohort = self._extract_incident_prevalent(
            self._extract_base_patient_cohort()
        )

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

        pop_size = len(self._patient_cohort[["ukrdcid"]].drop_duplicates())

        return DialysisStats(
            metadata=DialysisMetadata(
                population=pop_size,
                from_time=self.time_window[0],
                to_time=self.time_window[1],
            ),
            all_patients_home_therapies=self._calculate_all_home_therapies(),
            incident_home_therapies=self._calculate_incident_home_therapies(),
            prevalent_home_therapies=self._calculate_prevalent_home_therapies(),
            incentre_dialysis_frequency=self._calculate_dialysis_frequency(),
            incident_initial_access=self._calculate_access_incident(),
        )
