import datetime as dt

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.calculators.dialysis import DialysisStatsCalculator

from ukrdc_sqla.ukrdc import (
    DialysisSession,
    Patient,
    PatientRecord,
    Treatment,
    ModalityCodes,
)

from ..models.maps import (
    DoubleLabelled3d,
    Basic3dMetadata,
    AxisLabel3d,
    DoubleLabelled3dData,
)

from typing import Literal, Optional, Tuple, Union
from sqlalchemy import and_, func, or_, select, func
from sqlalchemy.orm import Session
import pandas as pd

from ..models.networks import LabelledNetwork, NetworkMetaData, Nodes, Connections
from ..models.base import JSONModel


class IncidentPrevalent(JSONModel):
    treatment_changes: LabelledNetwork
    modality_over_time: DoubleLabelled3d


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
    """class to calculate metrics associated with dialysis modalities"""

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

        # extract cohort from dialysis stats
        dialysis_calculator = DialysisStatsCalculator(
            self.session,
            self.facility,
            from_time=self.time_window[0],
            to_time=self.time_window[1],
        )

        dialysis_calculator.extract_patient_cohort()

        # apply window function to rank treatments by order of occurrence
        patient_cohort = dialysis_calculator._patient_cohort
        patient_cohort["rank"] = patient_cohort.groupby(
            ["ukrdcid", "registry_code_type", "qbl05"], dropna=False
        )["fromtime"].rank(ascending=True)

        return patient_cohort

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

        # replace na in case of no new event
        joined_events["Event_y"].fillna(joined_events["Event_x"], inplace=True)

        events_aggregated = (
            joined_events.groupby(["Event_x", "Event_y"]).count().reset_index()
        )

        # make sankey plot
        source_labels = list(events_aggregated["Event_x"].unique())
        target_labels = list(events_aggregated["Event_y"].unique())
        source = []
        target = []
        value = []
        for _, row in events_aggregated.iterrows():
            source.append(source_labels.index(row["Event_x"]))
            target.append(len(source_labels) + target_labels.index(row["Event_y"]))
            value.append(row["ukrdcid"])

        nodes = Nodes(node_labels=[*source_labels, *target_labels])

        connections = Connections(source=source, target=target, value=value)

        return nodes, connections

    def next_treatment(self):
        # calculate next treatment
        # TODO: incident prevalent filters etc

        nodes, connections = self._calculate_events()

        return LabelledNetwork(
            metadata=NetworkMetaData(
                title="Treatment Changes",
                summary="First Treatment modality change over the last three months",
                description=" ",
            ),
            node=nodes,
            link=connections,
        )

    def treatment_history(self, number_of_quarters: int):
        # this is horrible...redo!

        days_of_quarter = 90
        dates = [
            self.time_window[0] - dt.timedelta(days=days_of_quarter * i)
            for i in range(number_of_quarters, -1, -1)
        ]

        xdata = []
        ydata = []
        zdata = []
        for j in range(number_of_quarters):
            calculator = DialysisStatsCalculator(
                self.session,
                self.facility,
                from_time=dates[j],
                to_time=dates[j + 1],
            )
            calculator.extract_patient_cohort()
            modalities = calculator._calculate_therapies_prevalent_patients()

            ydata.extend(modalities.data.x)
            zdata.extend(modalities.data.y)
            xdata.extend([str(dates[j]) for _ in range(len(modalities.data.x))])

            del calculator

        return DoubleLabelled3d(
            metadata=Basic3dMetadata(
                title="",
                summary="",
                description="",
                axis_titles=AxisLabel3d(x="Quarter Start", y="Modality", z="Patients"),
            ),
            data=DoubleLabelled3dData(x=xdata, y=ydata, z=zdata),
        )

    def extract_patient_cohort(self):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        """
        self._patient_cohort = self._extract_base_patient_cohort()

    def extract_stats(self):

        # self.treatment_history(4)

        return IncidentPrevalent(
            treatment_changes=self.next_treatment(),
            modality_over_time=self.treatment_history(12),
        )
