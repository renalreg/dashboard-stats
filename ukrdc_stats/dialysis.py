from cmath import nan
import datetime as dt
from importlib.abc import PathEntryFinder
from typing import Dict, List, Tuple
from unittest import result
from xmlrpc.client import Boolean


import pandas as pd
import numpy as np

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func
from ukrdc_sqla.ukrdc import Patient, PatientRecord, Treatment, DialysisSession
from ukrdc_sqla.ukrdc import LabOrder, ResultItem
from ukrdc_stats.utils import dob_cutoff_from_age

from .models.networks import LabelledNetwork, Nodes, Vertices, NetworkMetaData
from .models.generic_2d import (
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
    AxisLabels2d,
)

from .models.maps import TimeSeries3dData, AxisLabel3d, Basic3dMetadata, TimeSeries3d

from pydantic import BaseModel


class DialysisStats(BaseModel):
    all_patients_home_therapies: LabelledNetwork
    incident_home_therapies: LabelledNetwork
    prevalent_home_therapies: LabelledNetwork
    incentre_dialysis_frequency: Labelled2d


class DialysisBiomarkers(BaseModel):
    incident_patients_haemoglobin: TimeSeries3dData
    prevalent_patients_egfr: TimeSeries3dData


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
            select(
                PatientRecord.ukrdcid,
                Patient.pid,
                Treatment.admit_reason_code,
                Treatment.qbl05,
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

    def _dialysis_frequency(self):
        # calculate the frequency with which dialysis occurs
        # get list of hd patients
        patient_list = self.patient_cohort[
            (self.patient_cohort.admitreasoncode.isin(["1", "2", "3"]))
            & (self.patient_cohort.qbl05 == "HOSP")
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
                    DialysisSession.procedure_time > self.timewindow[0],
                    DialysisSession.procedure_time < self.timewindow[1],
                )
            )
            .group_by(PatientRecord.ukrdcid)
        )
        session_data = pd.read_sql(query, self.session.bind)

        # calculate frequency of dialysis
        session_data["freq"] = session_data.apply(
            lambda row: self._calculate_frequency(
                row["fromtime"], row["totime"], row["sessioncount"]
            ),
            axis=1,
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
                axis_titles=AxisLabels2d(
                    x="Frequency (days per week)", y="No. of Patients"
                ),
            ),
            data=Labelled2dData(
                x=list(hist.keys()), y=[int(value) for value in hist.values]
            ),
        )

    def _calculate_frequency(
        self, from_time: dt.datetime, to_time: dt.datetime, procedure_number: int
    ):

        delta_t = (to_time - from_time).days

        if delta_t > 0.0:
            return 7.0 * procedure_number / delta_t
        else:
            return None

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
            incentre_dialysis_frequency=self._dialysis_frequency(),
        )

    def extract_biomarkers(self):

        return DialysisBiomarkers(
            incident_patients_haemoglobin=self._calculate_haemoglobin(
                filter=self.patient_cohort.incident == True
            ),
            prevalent_patients_egfr=self._calculate_egfr(
                filter=self.patient_cohort.prevalent == True
            ),
        )

    def _calculate_egfr(self, filter: List[Boolean]):

        filtered_patient_ids = self.patient_cohort[filter].ukrdcid.drop_duplicates()

        result_query = (
            select(
                PatientRecord.ukrdcid,
                Patient.birth_time,
                Patient.gender,
                LabOrder.entered_on,
                ResultItem.value,
                ResultItem.value_units,
            )
            .join(Patient, Patient.pid == PatientRecord.pid)
            .join(LabOrder, LabOrder.pid == PatientRecord.pid)
            .join(ResultItem, ResultItem.order_id == LabOrder.id)
            .where(
                and_(
                    PatientRecord.ukrdcid.in_(filtered_patient_ids),
                    ResultItem.service_id == "QBLA1",
                    LabOrder.entered_on > self.timewindow[0],
                    LabOrder.entered_on < self.timewindow[1],
                )
            )
        )

        result_data = pd.read_sql(result_query, self.session.bind)
        result_data["age"] = result_data.apply(
            lambda row: (row["enteredon"] - row["birthtime"]).days / 365.25, axis=1
        )

        result_data["egfr"] = result_data.apply(lambda row: self._row_egfr(row), axis=1)

        # we need a sensible way of ordering the data so it is readable in visulisations
        # to do this we order by the maximum egfr and replace the ukrdcids with a rank
        result_data_max = (
            result_data[["ukrdcid", "egfr"]]
            .groupby(["ukrdcid"], as_index=False)
            .max("egfr")
            .sort_values("egfr")
            .reset_index()
        )

        # substitute ukrdc id's for ranks
        map = {}
        for i, id in enumerate(result_data_max.ukrdcid):
            map[id] = i

        result_data["egfr_rank"] = result_data.ukrdcid.map(map)

        # print(result_data.head())
        # rint(result_data.rank)

        return TimeSeries3dData(
            x=list(result_data.enteredon),
            y=list(result_data.egfr_rank),
            z=list(result_data.egfr),
        )

    def _row_egfr(self, row):

        try:
            value = float(row["resultvalue"])
            egfr = 175.0 * (value / 88.4) ** -1.154 * row["age"] ** -0.203

            if row["gender"] == "2":
                0.742 * egfr

            egfr = int(round(egfr))
        except ValueError:
            egfr = None

        return egfr

    def _calculate_haemoglobin(self, filter: List[Boolean] = True):

        filtered_patient_ids = self.patient_cohort[filter].ukrdcid.drop_duplicates()

        # print(filtered_patient_ids)
        result_query = (
            select(
                PatientRecord.ukrdcid,
                Patient.birth_time,
                Patient.gender,
                LabOrder.entered_on,
                ResultItem.service_id,
                ResultItem.value,
                ResultItem.value_units,
            )
            .join(Patient, Patient.pid == PatientRecord.pid)
            .join(LabOrder, LabOrder.pid == PatientRecord.pid)
            .join(ResultItem, ResultItem.order_id == LabOrder.id)
            .where(
                and_(
                    PatientRecord.ukrdcid.in_(filtered_patient_ids),
                    ResultItem.service_id == "QBLEB",
                    LabOrder.entered_on > self.timewindow[0],
                    LabOrder.entered_on < self.timewindow[1],
                )
            )
        )

        result_data = pd.read_sql(result_query, self.session.bind)

        results = []
        times = []
        ids = []
        for index, item in result_data.iterrows():
            try:
                results.append(float(item.resultvalue))
            except ValueError:
                continue
            times.append(item.enteredon)
            ids.append(item.ukrdcid)

        # print(result_data.head())

        return TimeSeries3dData(
            x=times,
            y=ids,
            z=results,
        )
