import datetime as dt
from typing import Dict, List, Tuple
from xmlrpc.client import Boolean


import pandas as pd
import numpy as np

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from ukrdc_sqla.ukrdc import Patient, PatientRecord, Treatment
from ukrdc_stats.utils import dob_cutoff_from_age

from .models.networks import LabelledNetwork, Nodes, Vertices, NetworkMetaData

from pydantic import BaseModel


class DialysisStats(BaseModel):
    all_patients_home_therapies: LabelledNetwork
    incident_home_therapies: LabelledNetwork
    prevalent_home_therapies: LabelledNetwork

    # not sure why this line is nessary but it stopped pydantic moaning
    # class Config:
    #    arbitrary_types_allowed = True


class DialysisStatsCalculator:
    """class to calcuate metrics associated with dialysis modalities"""

    def __init__(self, session: Session, facility: str, timewindow: List[dt.datetime]):
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
        self.patient_cohort = self._extract_patient_cohort()
        self._incident_prevelent()

    def _extract_patient_cohort(self) -> pd.DataFrame:
        """

        Returns:
            pd.DataFrame: _description_
        """

        patient_query = (
            select(PatientRecord, Patient, Treatment)  # type:ignore
            .join(Treatment, Treatment.pid == Patient.pid)  # type:ignore
            .join(PatientRecord, PatientRecord.pid == Patient.pid)  # type:ignore
            .where(
                and_(
                    # filter for facility
                    Treatment.health_care_facility_code == self.facility,
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
        """For the patients calculate the incidence and prevelence.
        This is currently a draft version and probably needs careful reviewing"""

        # If patients are alive and have not died or been discharged count them as prevelent
        self.patient_cohort["prevalent"] = (
            pd.isnull(self.patient_cohort.deathtime)
            | (self.patient_cohort.deathtime > self.timewindow[1])
        ) & (
            (self.patient_cohort.totime > self.timewindow[1])
            | pd.isnull(self.patient_cohort.totime)
        )

        # Get a list of patients to check for incidence status
        incident_ids = self.patient_cohort[["ukrdcid"]][
            self.patient_cohort.fromtime > self.timewindow[0]
        ].drop_duplicates()

        # Run query to test if they have appeared as hd, pd, or Tx prior to beginning of window
        not_incident_ids_query = (
            select(PatientRecord.ukrdcid)
            .join(Treatment)
            .where(
                and_(
                    Treatment.admit_reason_code.in_(
                        ["1", "2", "3", "5", "11", "12", "20", "29", "78"]
                    ),
                    Treatment.from_time < self.timewindow[0],
                    PatientRecord.ukrdcid.in_(incident_ids.ukrdcid.to_numpy()),
                )
            )
        )
        not_incident_ids = self.session.execute(not_incident_ids_query).all()

        # label patient not appearing in previous group as incident
        incident_ids["incident"] = ~incident_ids.ukrdcid.isin(
            [id[0] for id in not_incident_ids]
        )

        # merge into patient cohort
        self.patient_cohort = pd.merge(self.patient_cohort, incident_ids, on="ukrdcid")

        return

    def _therapy_types(self, filter: List[Boolean] = True) -> Tuple[Nodes, Vertices]:

        """Breakdown of dialysis patients on home and in-centre therapies.
        The information is returned using pydantic classes designed handle networks (this is essentially what a sankey plot is)

        Args:
            filter (List[Boolean]): a filter to apply to the patient cohort. For example you could pass self.patient_cohort.incident ==True
        Returns:
            Nodes, Vertices: pydantic classes containing calculated data
        """

        hosp_hd = len(
            self.patient_cohort[
                filter
                & self.patient_cohort.admitreasoncode.isin(["1", "2", "3", "5"])
                & (self.patient_cohort.qbl05 == "HOSP")
            ]["ukrdcid"].drop_duplicates()
        )

        home_hd = len(
            self.patient_cohort[
                filter
                & self.patient_cohort.admitreasoncode.isin(["1", "2", "3", "5"])
                & (self.patient_cohort.qbl05 == "HOME")
            ]["ukrdcid"].drop_duplicates()
        )

        na_hd = len(
            self.patient_cohort[
                filter
                & self.patient_cohort.admitreasoncode.isin(["1", "2", "3", "5"])
                & self.patient_cohort.qbl05.isnull()
            ]["ukrdcid"].drop_duplicates()
        )

        # presumably all pd is done at home?
        home_pd = len(
            self.patient_cohort[
                filter & self.patient_cohort.admitreasoncode.isin(["11", "12"])
            ]["ukrdcid"].drop_duplicates()
        )

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
            source=[0, 0, 0, 1],
            target=[2, 3, 4, 2],
            value=[home_hd, hosp_hd, na_hd, home_pd],
        )

        return nodes, vertices

    def patient_flows(self):
        return

    def extract_stats(self):

        all_patients_nodes, all_patients_vertices = self._therapy_types()
        incident_nodes, incident_vertices = self._therapy_types(
            self.patient_cohort.incident == True
        )
        prevalent_nodes, prevalent_vertices = self._therapy_types(
            self.patient_cohort.prevalent == True
        )

        return DialysisStats(
            all_patients_home_therapies=LabelledNetwork(
                metadata=NetworkMetaData(
                    title="Proportion of all Dialysis Patients on Home Therapies"
                ),
                node=all_patients_nodes,
                link=all_patients_vertices,
            ),
            incident_home_therapies=LabelledNetwork(
                metadata=NetworkMetaData(
                    title="Proportion of Incident Patients on Home Therapies"
                ),
                node=incident_nodes,
                link=incident_vertices,
            ),
            prevalent_home_therapies=LabelledNetwork(
                metadata=NetworkMetaData(
                    title="Proportion of Prevalent Patients on Home Therapies"
                ),
                node=prevalent_nodes,
                link=prevalent_vertices,
            ),
        )
