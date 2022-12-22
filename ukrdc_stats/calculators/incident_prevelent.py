import datetime as dt

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_sqla.ukrdc import (
    DialysisSession,
    Patient,
    PatientRecord,
    Treatment,
    ModalityCodes,
)
from typing import Literal, Optional, Tuple, Union
from sqlalchemy import and_, func, or_, select, func
from sqlalchemy.orm import Session
import pandas as pd


def generate_death_and_discharge_events(extracted_data: pd.DataFrame) -> pd.DataFrame:

    death_events = extracted_data[~extracted_data.deathtime.isna()][
        ["ukrdcid", "deathtime"]
    ].drop_duplicates()
    death_events["Event"] = "Dead"
    death_events.rename(columns={"deathtime": "Event Time"}, inplace=True)

    discharge_events = extracted_data[~extracted_data.dischargereasoncode.isna()][
        ["ukrdcid", "totime"]
    ]
    discharge_events["Event"] = "Discharged"
    discharge_events.rename(columns={"totime": "Event Time"}, inplace=True)

    return pd.concat([death_events, discharge_events])


def generate_modality_start_events(extracted_data: pd.DataFrame) -> pd.DataFrame:

    # distinguish between HD types
    extracted_data.loc[
        (extracted_data.registry_code_type == "HD") & (extracted_data.qbl05 == "HOME"),
        "registry_code_type",
    ] = "HHD"

    extracted_data.loc[
        (extracted_data.registry_code_type == "HD")
        & ((extracted_data.qbl05 == "HOSP") | (extracted_data.qbl05 == "SATL")),
        "registry_code_type",
    ] = "ICHD"

    extracted_data.loc[
        (extracted_data.registry_code_type == "HD") & extracted_data.qbl05.isnull(),
        "registry_code_type",
    ] = "HD Unknown"

    # generate set of events based on the first instance of each event type
    treatment_events = extracted_data[extracted_data["rank"] == 1][
        ["ukrdcid", "registry_code_type", "fromtime"]
    ].drop_duplicates()
    treatment_events.rename(columns={"fromtime": "Event Time"}, inplace=True)
    treatment_events.rename(columns={"registry_code_type": "Event"}, inplace=True)

    return treatment_events


class IncidentPrevalentStatsCalculator(AbstractFacilityStatsCalculator):
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

        patient_query = (
            select(
                PatientRecord.ukrdcid,
                PatientRecord.pid,
                Patient.death_time,
                ModalityCodes.registry_code_type,
                Treatment.qbl05,
                Treatment.hdp04,
                Treatment.from_time,
                Treatment.to_time,
                Treatment.discharge_reason_code,
                # rank modalities in order they occurred
                func.rank()
                .over(
                    order_by=Treatment.from_time,
                    partition_by=(
                        PatientRecord.ukrdcid,
                        ModalityCodes.registry_code_type,
                        Treatment.qbl05,
                    ),
                )
                .label("rank"),
            )
            .join(Treatment, PatientRecord.pid == Treatment.pid)
            .join(Patient, Patient.pid == PatientRecord.pid)
            .join(
                ModalityCodes,
                ModalityCodes.registry_code == Treatment.admit_reason_code,
            )
            .where(
                and_(
                    # filter for facility
                    Treatment.health_care_facility_code == self.facility,
                    PatientRecord.sendingextract == "UKRDC",
                    # ensure patient is alive at beginning of time window
                    or_(
                        Patient.death_time.is_(None),
                        Patient.death_time > self.time_window[0],
                    ),
                    and_(
                        Treatment.from_time < self.time_window[1],
                        or_(
                            Treatment.to_time > self.time_window[0],
                            Treatment.to_time.is_(None),
                        ),
                    ),
                    or_(
                        ModalityCodes.registry_code_type == "TX",
                        ModalityCodes.registry_code_type == "HD",
                        ModalityCodes.registry_code_type == "PD",
                    ),
                )
            )
            .order_by(PatientRecord.ukrdcid, Treatment.from_time)
        )

        return pd.read_sql(patient_query, self.session.bind).drop_duplicates()

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

        # Run query to test if they have appeared as hd, pd, or Tx prior to beginning of window: these will be discounted
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

    def _calculate_events(self) -> pd.DataFrame():

        raw_events = pd.concat(
            [
                generate_death_and_discharge_events(self._patient_cohort),
                generate_modality_start_events(self._patient_cohort),
            ]
        )

        # rank events
        raw_events["Event Rank"] = raw_events.groupby(["ukrdcid"]).rank(method="dense")[
            "Event Time"
        ]

        # generate next event for patients
        joined_events = raw_events[raw_events["Event Rank"] == 1].merge(
            raw_events[raw_events["Event Rank"] == 2], on="ukrdcid", how="left"
        )

        """
        joined_events[joined_events["Event_y"].isnull()]["Event_y"] = joined_events[
            joined_events["Event_y"].isnull()
        ]["Event_x"]
        """

        # replace na in case of no new event
        joined_events["Event_y"].fillna(joined_events["Event_x"], inplace=True)

        events_aggregated = (
            joined_events.groupby(["Event_x", "Event_y"]).count().reset_index()
        )

        return events_aggregated.rename(
            columns={
                "ukrdcid": "Count",
                "Event_x": "Start Modality",
                "Event_y": "End Modality",
            }
        )[["Start Modality", "End Modality", "Count"]]

    def extract_patient_cohort(self):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        """
        self._patient_cohort = self._extract_incident_prevalent(
            self._extract_base_patient_cohort()
        )

    def extract_stats(self):
        return
