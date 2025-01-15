"""
Patient cohort dialysis stats calculator
"""

import datetime as dt


from typing import Optional, Tuple, List, Dict

import pandas as pd
from sqlalchemy import and_, func, or_, select, cast, case, exists
from sqlalchemy.orm import Session, aliased
from sqlalchemy.types import Float
from ukrdc_sqla.ukrdc import (
    DialysisSession,
    Patient,
    PatientRecord,
    Treatment,
    ModalityCodes,
)

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError
from pydantic import Field


from ukrdc_stats.descriptions import dialysis_descriptions
from ukrdc_stats.models.generic_2d import (
    AxisLabels2d,
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
    BaseTable,
)
from ukrdc_stats.models.base import JSONModel


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

    all_treatments_krt: Labelled2d = Field(
        ...,
        description="statistical breakdown of therapy types for all patients in cohort",
    )
    incident_krt: Labelled2d = Field(
        ...,
        description="statistical breakdown of therapy types for incident patients in cohort",
    )
    prevalent_krt: Labelled2d = Field(
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


class UnitLevelDialysisStats(JSONModel):
    all: DialysisStats
    units: Dict[str, DialysisStats]


class CohortReport(JSONModel):
    description: str
    cohort: str
    population: int
    table: BaseTable


def _calculate_frequency(
    from_time: dt.datetime,
    to_time: dt.datetime,
    no_of_events: int,
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


def calculate_therapy_types(
    patient_cohort: pd.DataFrame,
) -> Tuple[List[str], List[int]]:
    """
    Breakdown of dialysis patients on home and in-centre therapies.
    The information is returned using pydantic classes designed to handle
    networks (this is essentially what a sankey plot is).

    Args:
        patient_cohort: DataFrame containing patient data.

    Returns:
        Tuple of two lists:
        - labels: A list of strings describing the type of therapy.
        - patients: A list of counts of patients for each type of therapy.
    """

    # Define mappings for 'qbl05' column
    mappings = {"HOSP": "In-centre", "SATL": "In-centre", "HOME": "Home"}

    # Update 'qbl05' based on conditions
    patient_cohort.loc[
        patient_cohort.registry_code_type.isin(["PD", "TX"]), "qbl05"
    ] = ""
    patient_cohort.loc[
        (patient_cohort.registry_code_type == "HD")
        & (patient_cohort.qbl05.isna() | patient_cohort.qbl05 == ""),
        "qbl05",
    ] = "Unknown/Incomplete"
    patient_cohort.loc[:, "qbl05"] = patient_cohort["qbl05"].replace(mappings)

    # Group and count patients by 'registry_code_type' and 'qbl05'
    grouped_patients = (
        patient_cohort.groupby(["registry_code_type", "qbl05"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("registry_code_type")
    )

    # Create labels and patients lists
    labels = [
        f"{row.registry_code_type} {row.qbl05}".strip()
        for _, row in grouped_patients.iterrows()
    ]
    patients = grouped_patients["count"].tolist()

    return labels, patients


def adjust_next_fromtime(group: pd.DataFrame):

    """
    Utility function to adjust the next_fromtime in the case where there are
    overlaps in the treatment records.

    This function will blank the next_fromtime of all bar the last record in an
    overlapping group. Overlapping group ends when there is a gap not covered
    by treatment. The logic here is slightly fiddly.

    Args:
        group (_type_): _description_

    Returns:
        _type_: _description_
    """
    # skip any single record group
    group = group.reset_index(drop=True)
    if len(group) > 1:
        overlapping = False
        for i in range(len(group) - 1):

            if overlapping:
                ind_final = i
                to_time = group.at[i, "totime"]
                if to_time > max_to_time:
                    max_to_time = group.at[i, "totime"]

                # overlap group ends where maximum to time in group is less
                # than the next from time.
                next_fromtime = group.at[i, "next_fromtime"]
                if max_to_time <= next_fromtime:
                    overlapping = False

                    # step 2: blank all next_fromtime in overlapping group
                    group.loc[ind_first:ind_final, "next_fromtime"] = pd.NaT

                    # step 3: select record with maximum totime and add
                    # next_fromtime back in
                    overlap_slice = group[ind_first : ind_final + 1]
                    max_totime_idx = overlap_slice["totime"].idxmax()
                    group.loc[max_totime_idx, "next_fromtime"] = next_fromtime

            else:
                # step 1: detect any overlapping records in group
                # locate the first record that satisfies the condition
                if group.at[i, "next_fromtime"] < group.at[i, "totime"]:
                    # create indices to track group
                    overlapping = True
                    ind_first = i
                    ind_final = i
                    max_to_time = group.at[i, "totime"]

    return group


class KRTStatsCalculator(AbstractFacilityStatsCalculator):
    """Class to calculate basic statistics associated with the renal
    replacement therapies for renal facility in a given time window."""

    def __init__(
        self,
        session: Session,
        facility: str,
        from_time: dt.datetime,
        to_time: dt.datetime,
    ):
        if to_time > dt.datetime.now() - dt.timedelta(days=90):
            raise Exception("cannot calculate stats within 90 of today")

        super().__init__(session, facility)

        # Create a precisely 2 element time window tuple
        self.time_window: Tuple[dt.datetime, dt.datetime] = (from_time, to_time)

        # defines encoding of KRT treatment types
        self.registry_code_types: List[str] = ["HD", "PD", "TX"]
        self.home_therapy_code_types: List[str] = ["HOSP", "SATL", "INCENTRE"]

    def extract_patient_cohort(self, limit_to_ukrdc: Optional[bool] = True):
        """
        Extract a complete patient cohort dataframe. This is calculated fresh
        each time but we would probably want to implement some caching here.
        """
        self._patient_cohort = self._extract_incident_prevalent(
            self._extract_base_patient_cohort(limit_to_ukrdc=limit_to_ukrdc)
        )

    def _extract_base_patient_cohort(
        self,
        limit_to_ukrdc: Optional[bool] = True,
    ) -> pd.DataFrame:
        """Core query from which the other stats is derived. All patients at a
        renal facility with treatments up to and including 90 days post and
        prior to the time window will be included into the base cohort. Query
        will also flag any patients which had a historical ckd diagnosis or
        transplant. This should be rigorously back tested with real data and
        any changes should be considered breaking changes only to be done in a
        major release.

        Returns:
            pd.DataFrame: Patient cohort dataframe
        """

        MINIMUM_TRANSPLANT_LENGTH = 7

        ChronicTreatment = aliased(Treatment)
        ChronicModality = aliased(ModalityCodes)
        HistoricTransplantTreatment = aliased(Treatment)
        TransplantModality = aliased(ModalityCodes)

        query = (
            select(
                PatientRecord.pid,
                Treatment.healthcarefacilitycode,
                Treatment.admitreasoncode,
                Treatment.admitreasoncodestd,
                Treatment.admissionsourcecode,
                Treatment.admissionsourcecodestd,
                Treatment.qbl05,
                Treatment.hdp04,
                Treatment.dischargereasoncode,
                Treatment.dischargelocationcodestd,
                ModalityCodes.registry_code_type,
                Patient.deathtime,
                Treatment.fromtime,
                Treatment.totime,
                # Correlated subquery for chronic treatment check
                case(
                    (
                        exists().where(
                            ChronicTreatment.pid == PatientRecord.pid,
                            ChronicTreatment.fromtime
                            < self.time_window[1],  # Check if within time window
                            ChronicTreatment.admitreasoncode
                            == ChronicModality.registry_code,  # Match chronic modality code
                            ChronicModality.registry_code_type == "CK",
                        ),
                        True,
                    ),
                    else_=False,
                ).label("is_chronic"),
                # Correlated subquery for historical transplant check
                case(
                    (
                        exists().where(
                            HistoricTransplantTreatment.pid == PatientRecord.pid,
                            HistoricTransplantTreatment.fromtime
                            < self.time_window[0],  # Before start of time window
                            HistoricTransplantTreatment.totime
                            - HistoricTransplantTreatment.fromtime
                            > dt.timedelta(
                                days=MINIMUM_TRANSPLANT_LENGTH
                            ),  # Successful transplant
                            HistoricTransplantTreatment.admitreasoncode
                            == TransplantModality.registry_code,
                            TransplantModality.registry_code_type == "TX",
                        ),
                        True,
                    ),
                    else_=False,
                ).label("historic_tx"),
            )
            .select_from(PatientRecord)
            .join(Patient, Patient.pid == PatientRecord.pid)
            .join(Treatment, Treatment.pid == PatientRecord.pid)
            .join(
                ModalityCodes, ModalityCodes.registry_code == Treatment.admitreasoncode
            )
            .where(
                ModalityCodes.registry_code_type.in_(self.registry_code_types),
                Treatment.fromtime < self.time_window[1] + dt.timedelta(days=90),
                or_(
                    Treatment.totime > self.time_window[0] - dt.timedelta(days=90),
                    Treatment.totime.is_(None),
                ),
                or_(
                    Patient.deathtime > self.time_window[0], Patient.deathtime.is_(None)
                ),
                PatientRecord.sendingfacility == self.facility,
            )
        )

        if limit_to_ukrdc:
            query = query.where(PatientRecord.sendingextract == "UKRDC")

        # Execute query
        base_cohort = pd.DataFrame(self.session.execute(query)).drop_duplicates()

        # pandas by default tries to be helpful and create compound keys
        # this is more overly helpful so we drop them
        base_cohort = base_cohort.reset_index(drop=True)

        return base_cohort

    def _chain_treatments(self, raw_patients: pd.DataFrame):
        """We append columns to the dataframe to allow recovery based
        calculations to be made.
        """

        raw_patients = raw_patients.sort_values(by=["pid", "fromtime"])

        # append the start of the next treatment to each record
        raw_patients["next_fromtime"] = raw_patients.groupby("pid")["fromtime"].shift(
            -1
        )

        raw_patients = raw_patients.groupby("pid", as_index=False).apply(
            adjust_next_fromtime
        )

        return raw_patients

    def _exclude_records(self, base_cohort: pd.DataFrame):
        """This implements any conditions the might cause a patient to be removed from
        the cohort. For example anyone who is in a 90 recovery period which spans the
        end of the time window should be excluded. Any patient with treatment modality
        code which implies CKD that dies before the end of the window will also be
        excluded.
        """

        # recovery window
        recoveries = (
            base_cohort["next_fromtime"] - base_cohort["totime"]
        ) > dt.timedelta(days=90)
        patient_recoveries = base_cohort[recoveries][["pid", "next_fromtime", "totime"]]

        index_to_remove = []
        for _, row in patient_recoveries.iterrows():
            if row["totime"] >= self.time_window[1]:
                # patient has made a recovery remove future records
                index_to_remove.extend(
                    base_cohort[
                        (base_cohort["pid"] == row["pid"])
                        & (base_cohort["fromtime"] > row["totime"])
                    ].index
                )
            else:
                if row["next_fromtime"] > self.time_window[1]:
                    # patient was recovered at end of window remove completely
                    index_to_remove.extend(
                        base_cohort[base_cohort["pid"] == row["pid"]].index
                    )

                else:
                    # patient coming out of recovery, remove record and all prior
                    index_to_remove.extend(
                        base_cohort[
                            (base_cohort["pid"] == row["pid"])
                            & (base_cohort["totime"] <= row["totime"])
                        ].index
                    )

        base_cohort = base_cohort.drop(index=index_to_remove)

        return base_cohort

    def _add_helper_columns(self, base_cohort: pd.DataFrame):
        """Function to postprocess data and add column to help with the
        calculation of incident and prevalent cohorts.

        Args:
            base_cohort (pd.DataFrame): Raw patient cohort generated by
            directly querying the database into pandas.

        Returns:
            _type_: _description_
        """

        # run function to link each treatment to the one that follows
        base_cohort = self._chain_treatments(base_cohort)

        # Exclude "acute" patients and records post or prior to recoveries
        base_cohort = self._exclude_records(base_cohort)

        # identify the records with the most recent from time for each pid
        most_recent = base_cohort[
            base_cohort["fromtime"] < self.time_window[1]
        ].reset_index(drop=True)
        most_recent = most_recent.groupby("pid", as_index=False)["fromtime"].max()

        # Merge with the original cohort to identify the most recent treatments
        base_cohort = base_cohort.merge(
            most_recent, on=["pid"], how="left", suffixes=("", "_max")
        )
        base_cohort["most_recent"] = (
            base_cohort["fromtime"] == base_cohort["fromtime_max"]
        )

        # add column which is true if recorded is first from time for a given pid
        base_cohort["first_treatment"] = (
            base_cohort.groupby("pid")["fromtime"].transform("min")
            == base_cohort["fromtime"]
        )

        return base_cohort

    def _extract_incident_prevalent(self, base_cohort: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a base cohort from _extract_base_patient_cohort and extracts the incident and prevalent patients.
        This is currently a draft version and probably needs careful reviewing.

        Args:
            base_cohort (pd.DataFrame): Base cohort from output of _extract_base_patient_cohort
        Returns:
            pd.DataFrame: Patient cohort dataframe
        """

        # Generate some helper columns to make it easier to calculate incidence
        # and prevalence
        base_cohort = self._add_helper_columns(base_cohort)

        # we calculate the beginning and end of each continuous/uninterrupted treatment period
        # At this point each patient should only have one of them. 
        
        # replace totime= na with today 
        base_cohort["totime"] = base_cohort["totime"].fillna(dt.datetime.now())
        base_cohort["timeline_start"] = base_cohort.groupby("pid", as_index=False)[
            "fromtime"
        ].transform("min")
        base_cohort["timeline_stop"] = base_cohort.groupby("pid", as_index=False)[
            "totime"
        ].transform("max")

        base_cohort["timeline_length"] = (
            base_cohort["timeline_stop"] - base_cohort["timeline_start"]
        )
        base_cohort["life_length"] = (
            base_cohort["deathtime"] - base_cohort["timeline_start"]
        )

        # prevalent cohort includes everyone who's treatment block spans the end of the time window
        # who is not acute. Acute patients must meet the same criterion with the addition of being
        # on KRT for more than 90 days.
        base_cohort["prevalent"] = (
            (base_cohort["timeline_start"] < self.time_window[1])
            & (
                (base_cohort["timeline_stop"] > self.time_window[1])
                | base_cohort["timeline_stop"].isna()
            )
            & base_cohort["is_chronic"]
        )

        # Without full coverage we can do anything super accurate with transfer
        # out. However we will treat certain dischargereason codes as idicating 
        # continued treatment. 
        discharge_reasons = ["38"]
        tranfered_pids = base_cohort[base_cohort["dischargereasoncode"].isin(discharge_reasons) & base_cohort.most_recent].pid.drop_duplicates()
        transfered_out = base_cohort.pid.isin(tranfered_pids)

        # Crash landed patients are defined:
        # - no chronic treatment records or tx
        # - remains on KRT for more than 90 days
        # - survives for more than 90 days  
        is_crash_landing = (
            (~base_cohort["is_chronic"] & ~base_cohort["historic_tx"])
            & (
                (base_cohort["timeline_length"] > dt.timedelta(days=90))
                | base_cohort["timeline_length"].isna()
                | transfered_out
            )
            & (
                (base_cohort["life_length"] > dt.timedelta(days=90))
                | base_cohort["life_length"].isna()                
            )
        )

        # Patients with a previous record of transplant or ckd are considered
        # planned for KRT. These patients must stay on KRT for more than 90
        # days or die to be counted as incident.
        planned_ckd = (
            (base_cohort["is_chronic"] | base_cohort["historic_tx"])
            & ( 
                (base_cohort["timeline_length"] > dt.timedelta(days=90))
                | base_cohort["timeline_length"].isna()
                | transfered_out
            )
            | (base_cohort["life_length"] < dt.timedelta(days=90))
        )

        base_cohort["incident"] = (
            (planned_ckd | is_crash_landing) 
            & (base_cohort["timeline_start"] > self.time_window[0])
            & (base_cohort["timeline_start"] <= self.time_window[1])
        )

        # Prevalence point defined at the end of the window patients are
        # counted as prevalent if their treatment timeline spans the end of the
        # window and is greater than 90 days.
        base_cohort["prevalent"] = (
            (base_cohort["timeline_start"] <= self.time_window[1])
            & (base_cohort["timeline_stop"] > self.time_window[1])
            & (base_cohort["timeline_length"] > dt.timedelta(days=90))
        )

        # debug
        debug_crash_landing = base_cohort[is_crash_landing]
        debug_planned_ckd = base_cohort[planned_ckd]

        return base_cohort

    def _calculate_dialysis_frequency(self, subunit: str = "all") -> Labelled2d:
        """_summary_

        Args:
            subunit (str, optional): _description_. Defaults to "all".

        Returns:
            Labelled2d: _description_
        """

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        patient_list = self._patient_cohort[
            (self._patient_cohort.registry_code_type == "HD")
            & (self._patient_cohort.qbl05.isin(["HOSP", "SATL", "In-centre"]))
        ]

        if subunit != "all":
            patient_list = patient_list[
                patient_list.healthcarefacilitycode == subunit
            ].pid.drop_duplicates()
        else:
            patient_list = patient_list.pid.drop_duplicates()

        # get number of dialysis sessions per patient and the date of the first and last one
        query = (
            select(
                PatientRecord.pid,
                func.min(DialysisSession.procedure_time).label("fromtime"),
                func.max(DialysisSession.procedure_time).label("totime"),
                func.count(DialysisSession.procedure_type_code).label("sessioncount"),
                func.sum(cast(DialysisSession.qhd31, Float)),
            )
            .join(DialysisSession, DialysisSession.pid == PatientRecord.pid)
            .where(
                and_(
                    PatientRecord.pid.in_(patient_list),
                    DialysisSession.procedure_type_code == "302497006",  # filter for hd
                    DialysisSession.procedure_time > self.time_window[0],
                    DialysisSession.procedure_time < self.time_window[1],
                )
            )
            .group_by(PatientRecord.pid)
        )

        session_data = pd.DataFrame(self.session.execute(query)).drop_duplicates()

        # calculate frequency of dialysis by function to rows
        # this function takes the number of sessions and dividing by a time period
        # the time period is defined by the difference between the first and last session

        if len(session_data) > 0:
            session_data["freq"] = session_data[session_data.sessioncount > 1].apply(
                lambda row: _calculate_frequency(
                    row["fromtime"], row["totime"], row["sessioncount"]
                ),
                axis=1,
                result_type="reduce",
            )
        else:
            # Create an empty freq column if the DataFrame is empty
            session_data["freq"] = pd.Series(dtype="float64")

        # Make a histogram of the dialysis frequency
        bins = [0.5, 1.5, 2.5, 3.5, 7.0]
        labels = ["1", "2", "3", ">3"]

        hist = pd.cut(session_data.freq, bins=bins, labels=labels).value_counts(
            sort=False
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="In-Centre Dialysis Frequency",
                summary="Histogram of frequency of dialysis per week.",
                description=dialysis_descriptions["INCENTRE_DIALYSIS_FREQ"],
                axis_titles=AxisLabels2d(
                    x="Frequency (days per week)", y="No. of Patients"
                ),
            ),
            data=Labelled2dData(
                x=list(hist.keys()), y=[int(value) for value in hist.values]
            ),
        )

    def _calculate_access_incident(self, subunit: str = "all") -> Labelled2d:
        """Displays the vascular access of incident patients on their first dialysis session
        Args:
            subunit (str, optional): Satellite unit. Defaults to "all".
        Raises:
            NoCohortError: e.g. if extract_patient_cohort has not been run
        Returns:
            Labelled2d: Number of incident patients with each type of access
        """

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # filter by subunit
        if subunit != "all":
            patient_list = self._patient_cohort[
                self._patient_cohort.incident
                & (self._patient_cohort.healthcarefacilitycode == subunit)
                # & self._patient_cohort.firsttreatment
            ].pid.drop_duplicates()
        else:
            patient_list = self._patient_cohort[
                self._patient_cohort.incident  # & self._patient_cohort.firsttreatment
            ].pid.drop_duplicates()

        window = (
            select(
                PatientRecord.pid,
                DialysisSession.procedure_time,
                DialysisSession.qhd20,
                func.rank()
                .over(
                    order_by=DialysisSession.procedure_time,
                    partition_by=PatientRecord.pid,
                )
                .label("rnk"),
            )
            .join(DialysisSession, DialysisSession.pid == PatientRecord.pid)
            .where(
                PatientRecord.pid.in_(
                    # pylint: disable=singleton-comparison
                    patient_list
                )
            )
        ).subquery()

        # query to select the type of access used on the first session
        initial_access_query = (
            select(window.c.qhd20, func.count(window.c.pid).label("no"))
            .group_by(window.c.qhd20)
            .where(window.c.rnk == 1)
        )

        initial_access_data = pd.DataFrame(
            self.session.execute(initial_access_query)
        ).drop_duplicates()

        if len(initial_access_data) > 0:
            initial_access_data.loc[
                initial_access_data.qhd20.isna(), "qhd20"
            ] = "Unknown/Incomplete"

            x_data = list(initial_access_data.qhd20)
            y_data = list(initial_access_data.no)
        else:
            x_data = []
            y_data = []

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Vascular Access on First HD Session",
                summary="Vascular access for incident patients registered on their first dialysis session.",
                description=dialysis_descriptions["INCIDENT_INITIAL_ACCESS"],
                axis_titles=AxisLabels2d(x="Line Type", y="No. of Patients"),
                population_size=0,
            ),
            data=Labelled2dData(x=x_data, y=y_data),
        )

    def _calculate_therapies_all_patients(self, subunit: str = "all") -> Labelled2d:
        """Calculate breakdown of therapy types for all
        Args:
            subunit (str, optional): Satellite unit. Defaults to "all".
        Raises:
            NoCohortError: _description_
        Returns:
            Labelled2d: Breakdown of all patients
        """

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        if subunit == "all":
            all_patients_labels, all_patients_no = calculate_therapy_types(
                self._patient_cohort
            )
        else:
            all_patients_labels, all_patients_no = calculate_therapy_types(
                self._patient_cohort[
                    self._patient_cohort.healthcarefacilitycode == subunit
                ]
            )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="All KRT Modalities",
                summary="Breakdown of all patients on both PD and HD, and by home therapies and in-centre therapies.",
                description=dialysis_descriptions["ALL_PATIENTS_HOME_THERAPIES"],
                population_size=sum(all_patients_no),
            ),
            data=Labelled2dData(x=all_patients_labels, y=all_patients_no),
        )

    def _calculate_therapies_incident_patients(
        self, subunit: str = "all"
    ) -> Labelled2d:
        """Wrapper for calculate_therapy_types to calculate therapy types for an incident cohort
        Args:
            subunit (str, optional): Satellite unit. Defaults to "all".
        Raises:
            NoCohortError: _description_
        Returns:
            Labelled2d: Types of dialysis for incident patient cohort
        """

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        if subunit == "all":
            incident_cohort = self._patient_cohort[
                self._patient_cohort.incident & self._patient_cohort.first_treatment
            ]
        else:
            incident_cohort = self._patient_cohort[
                self._patient_cohort.incident
                & (self._patient_cohort.healthcarefacilitycode == subunit)
                & self._patient_cohort.first_treatment
            ]

        incident_labels, incident_no = calculate_therapy_types(incident_cohort)

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Incident KRT Modalities",
                summary="Breakdown of incident patients on PD and HD, and by home therapies and in-centre therapies.",
                description=dialysis_descriptions["INCIDENT_HOME_THERAPIES"],
                population_size=sum(incident_no),
            ),
            data=Labelled2dData(x=incident_labels, y=incident_no),
        )

    def _calculate_therapies_prevalent_patients(self, subunit: str = "all"):
        """Wrapper for calculate_therapy_types to calculate therapy types for an prevalent cohort
        Args:
            subunit (str, optional): Satellite unit. Defaults to "all".
        Raises:
            NoCohortError: _description_
        Returns:
            Labelled2d: Types of dialysis for prevalent patient cohort
        """

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # filter patient cohort to get the last treatment of each prevalent patient
        if subunit == "all":
            prevalent_cohort = self._patient_cohort[
                self._patient_cohort.prevalent & self._patient_cohort.most_recent
            ]

        else:
            prevalent_cohort = self._patient_cohort[
                self._patient_cohort.prevalent
                & self._patient_cohort.most_recent
                & (self._patient_cohort.healthcarefacilitycode == subunit)
            ]

        prevalent_labels, prevalent_no = calculate_therapy_types(prevalent_cohort)

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Prevalent KRT Modalities",
                summary="Breakdown of prevalent patients by PD and HD, and by home therapies and in-centre therapies.",
                description=dialysis_descriptions["PREVALENT_HOME_THERAPIES"],
                population_size=sum(prevalent_no),
            ),
            data=Labelled2dData(x=prevalent_labels, y=prevalent_no),
        )

    def extract_satellite_stats(self, unit: str = "all") -> DialysisStats:
        """
        Returns:
            DialysisStats:
        """

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # what should we use as the
        pop_size = 0
        # pop_size = None
        # pop_size = len(self._patient_cohort.ukrdcid.unique())

        return DialysisStats(
            metadata=DialysisMetadata(
                population=pop_size,
                from_time=self.time_window[0],
                to_time=self.time_window[1],
            ),
            all_treatments_krt=self._calculate_therapies_all_patients(subunit=unit),
            incident_krt=self._calculate_therapies_incident_patients(subunit=unit),
            prevalent_krt=self._calculate_therapies_prevalent_patients(subunit=unit),
            incentre_dialysis_frequency=self._calculate_dialysis_frequency(
                subunit=unit
            ),
            incident_initial_access=self._calculate_access_incident(subunit=unit),
        )

    def extract_stats(
        self,
        limit_to_ukrdc: Optional[bool] = True,
    ) -> UnitLevelDialysisStats:
        """Extract all stats for the dialysis module
        Returns:
            DialysisStats: Dialysis statistics object
        """
        # If we don't already have a patient cohort, extract one

        if self._patient_cohort is None:
            self.extract_patient_cohort(
                limit_to_ukrdc=limit_to_ukrdc,
            )

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # calculate stats for all units
        unit_stats: Dict[str, DialysisStats] = {}

        # loop over each unit and calculate stats
        for unit in self._patient_cohort.healthcarefacilitycode.unique():
            if unit:
                unit_stats[unit] = self.extract_satellite_stats(unit)
            else:
                unit_stats["Unknown/Incomplete"] = self.extract_satellite_stats(unit)

        return UnitLevelDialysisStats(
            all=self.extract_satellite_stats(), units=unit_stats
        )

    def generate_cohort_report(
        self, cohort: str, include_ni: bool = False
    ) -> BaseTable:
        """

        Args:
            cohort (str): _description_

        Returns:
            BaseTable: _description_
        """

        # check we have done the extract
        if self._patient_cohort is None:
            _ = self.extract_stats()

        # check the centre is in the output
        if cohort == "incident":
            pop, report = self.produce_report(
                [cohort, "first_treatment"],
                [
                    "pid",
                    "healthcarefacilitycode",
                    "admitreasoncode",
                    "admitreasoncodestd",
                    "registry_code_type",
                ],
                include_ni=include_ni,
            )
        elif cohort == "prevalent":
            pop, report = self.produce_report(
                [cohort, "most_recent"],
                [
                    "pid",
                    "healcarefacilitycode",
                    "admitreasoncode",
                    "admitreasoncodestd",
                    "registry_code_type",
                ],
                include_ni=include_ni,
            )

        desc = f"Report on the treatment modalities of the {cohort} cohort. This report contains a table which includes the most recent treatment modality and the way it's classified by the renal registry along with the ukrdc patient identifier."

        return CohortReport(
            description=desc, cohort=cohort, population=pop, table=report
        )
