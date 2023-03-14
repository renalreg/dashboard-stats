"""
Patient cohort dialysis stats calculator
"""

import datetime as dt

from typing import Optional, Tuple, List, Dict

import pandas as pd
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
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


from ..models.generic_2d import (
    AxisLabels2d,
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
)

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

    all_patients_home_therapies: Labelled2d = Field(
        ...,
        description="statistical breakdown of therapy types for all patients in cohort",
    )
    incident_home_therapies: Labelled2d = Field(
        ...,
        description="statistical breakdown of therapy types for incident patients in cohort",
    )
    prevalent_home_therapies: Labelled2d = Field(
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
    The information is returned using pydantic classes designed handle
    networks (this is essentially what a sankey plot is)
    Args:
        Scope: allows stats to be calculated for incident, prevalent or all patients
    Returns:
        Nodes, Connections: pydantic classes containing calculated data
    """

    # Count patients based on modalities
    # TODO: Maybe some of these lines should be moved to extract patient cohort or something like that

    patient_cohort.loc[patient_cohort.registry_code_type == "PD", "qbl05"] = ""
    patient_cohort.loc[patient_cohort.registry_code_type == "TX", "qbl05"] = ""
    patient_cohort.loc[
        (patient_cohort.registry_code_type == "HD") & patient_cohort.qbl05.isna(),
        "qbl05",
    ] = "Unknown/Incomplete"

    patient_cohort.loc[patient_cohort.qbl05 == "HOSP", "qbl05"] = "In-centre"

    patient_cohort.loc[patient_cohort.qbl05 == "SATL", "qbl05"] = "In-centre"
    patient_cohort.loc[patient_cohort.qbl05 == "HOME", "qbl05"] = "Home"

    # Duplicated rows shouldn't exist at this point anyway
    # This should catch them if they do

    grouped_patients = (
        patient_cohort.drop_duplicates()
        .groupby(["registry_code_type", "qbl05"], as_index=False)
        .count()[["ukrdcid", "registry_code_type", "qbl05"]]
        .sort_values("registry_code_type")
    )

    labels = []
    patients = []
    for _, row in grouped_patients.iterrows():
        labels.append(f"{row.registry_code_type} {row.qbl05}".rstrip())
        patients.append(row.ukrdcid)

    return labels, patients


class DialysisStatsCalculator(AbstractFacilityStatsCalculator):
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

    def _extract_base_patient_cohort(
        self,
        limit_to_ukrdc: Optional[bool] = True,
        limit_query_length: Optional[int] = None,
    ) -> pd.DataFrame:
        """Extract a base patient cohort dataframe from the database
        Returns:
            pd.DataFrame: Patient cohort dataframe
        """

        patient_query = (
            select(
                PatientRecord.ukrdcid,
                PatientRecord.sendingextract,
                Patient.pid,
                Treatment.health_care_facility_code,
                ModalityCodes.registry_code_type,
                Treatment.admit_reason_code,
                Treatment.qbl05,
                Treatment.hdp04,
                Treatment.from_time,
                Treatment.to_time,
                Patient.death_time,
                Treatment.discharge_reason_code,
            )  # type:ignore
            .join(Treatment, Treatment.pid == Patient.pid)  # type:ignore
            .join(PatientRecord, PatientRecord.pid == Patient.pid)  # type:ignore
            .join(
                ModalityCodes,
                ModalityCodes.registry_code == Treatment.admit_reason_code,
            )
            .where(
                and_(
                    # filter for facility,
                    PatientRecord.sendingfacility == self.facility,
                    PatientRecord.sendingextract == "UKRDC",
                    # ensure patient is alive at beginning of time window
                    or_(
                        Patient.death_time.is_(None),
                        Patient.death_time > self.time_window[0],
                    ),
                    # filter on dialysis modalities
                    or_(
                        ModalityCodes.registry_code_type == "HD",
                        ModalityCodes.registry_code_type == "PD",
                        ModalityCodes.registry_code_type == "TX",
                    ),
                    # filter on treatment start time
                    and_(
                        Treatment.from_time < self.time_window[1],
                        or_(
                            Treatment.to_time > self.time_window[0],
                            Treatment.to_time.is_(None),
                        ),
                    ),
                )
            )
        )

        # limit stats to ukrdc
        if limit_to_ukrdc:
            patient_query.where(PatientRecord.sendingextract == "UKRDC")

        # limit number of records returned (for benchmarking)
        if limit_query_length:
            patients = next(
                pd.read_sql(
                    patient_query, self.session.bind, chunksize=limit_query_length
                ).drop_duplicates()
            )

        else:
            patients = pd.read_sql(patient_query, self.session.bind).drop_duplicates()

        # determine first and last treatment
        # I think this logic falls over with treatments of the first start date
        # rank treatments by date. It needs careful thinking about but if two treatments
        # have the same rank then they would both be counted as say the first treatment.
        # this would result in a double count. Such double counts would be very
        # pathalogical so I don't think they are a currently a priority.

        patients["treatmentrank"] = (
            patients.groupby(
                "ukrdcid",
            )
            .rank()
            .fromtime
        )

        # identify minimum (in principle this is overkill but first item may not have rank of 1 )
        # see todo
        patients["rankmin"] = patients.groupby(["ukrdcid"])["treatmentrank"].transform(
            min
        )

        # identify maximum
        patients["rankmax"] = patients.groupby(["ukrdcid"])["treatmentrank"].transform(
            max
        )

        # use max and min to identify first and last treatment
        patients["firsttreatment"] = patients["rankmin"] == patients["treatmentrank"]
        patients["lasttreatment"] = patients["rankmax"] == patients["treatmentrank"]

        # drop helper columns
        return patients.drop(columns=["treatmentrank", "rankmin", "rankmax"])

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
            .join(Treatment, PatientRecord.pid == Treatment.pid)
            .join(
                ModalityCodes,
                ModalityCodes.registry_code == Treatment.admit_reason_code,
            )
            .where(
                and_(
                    or_(
                        ModalityCodes.registry_code_type == "HD",
                        ModalityCodes.registry_code_type == "PD",
                        ModalityCodes.registry_code_type == "Tx",
                    ),
                    Treatment.admission_source_code.is_(
                        None
                    ),  # Patients transferred in from another unit
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

    def _calculate_dialysis_frequency(self, subunit: str = "all") -> Labelled2d:

        """Calculate the per week frequency with which dialysis occurs.
        Raises:
            NoCohortError: e.g if extract_patient_cohort has not been run
        Returns:
            Labelled2d: returns histogram of dialysis frequency with nbins as the number of bins
        """

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # filter the patient cohort down to in-centre "HD patients"
        # Is this necessary? will non in-centre HD patients have dialysis sessions?
        patient_list = self._patient_cohort[
            (self._patient_cohort.registry_code_type == "HD")
            & (self._patient_cohort.qbl05 == "In-centre")
        ]

        # filter on satellite unit
        if subunit != "all":
            patient_list = patient_list[
                patient_list.healthcarefacilitycode == subunit
            ].ukrdcid.drop_duplicates()
        else:
            patient_list = patient_list.ukrdcid.drop_duplicates()

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

        # calculate frequency of dialysis by function to rows
        # this function takes the number of sessions and dividing by a time period
        # the time period is defined by the difference between the first and last session
        session_data["freq"] = session_data[session_data.sessioncount > 1].apply(
            lambda row: _calculate_frequency(
                row["fromtime"], row["totime"], row["sessioncount"]
            ),
            axis=1,
            result_type="reduce",
        )

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
            ].ukrdcid.drop_duplicates()
        else:
            patient_list = self._patient_cohort[
                self._patient_cohort.incident  # & self._patient_cohort.firsttreatment
            ].ukrdcid.drop_duplicates()

        # print(len(patient_list))

        # window function to rank the procedures in the order they happened
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
                    patient_list
                )
            )
        ).subquery()

        # query to select the type of access used on the first session
        initial_access_query = (
            select(window.c.qhd20, func.count(window.c.ukrdcid).label("no"))
            .group_by(window.c.qhd20)
            .where(window.c.rnk == 1)
        )

        initial_access_data = pd.read_sql(initial_access_query, self.session.bind)

        initial_access_data.loc[
            initial_access_data.qhd20.isna(), "qhd20"
        ] = "Unknown/Incomplete"

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Vascular Access on First HD Session",
                summary="Vascular access for incident patients registered on their first dialysis session.",
                description=dialysis_descriptions["INCIDENT_INITIAL_ACCESS"],
                axis_titles=AxisLabels2d(x="Line Type", y="No. of Patients"),
                population_size=sum(list(initial_access_data.no)),
            ),
            data=Labelled2dData(
                x=list(initial_access_data.qhd20), y=list(initial_access_data.no)
            ),
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
                self._patient_cohort.incident & self._patient_cohort.firsttreatment
            ]
        else:
            incident_cohort = self._patient_cohort[
                self._patient_cohort.incident
                & (self._patient_cohort.healthcarefacilitycode == subunit)
                & self._patient_cohort.firsttreatment
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
                self._patient_cohort.prevalent & self._patient_cohort.lasttreatment
            ]

        else:
            prevalent_cohort = self._patient_cohort[
                self._patient_cohort.prevalent
                & self._patient_cohort.lasttreatment
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

    def extract_patient_cohort(
        self,
        limit_to_ukrdc: Optional[bool] = True,
        limit_query_length: Optional[int] = None,
    ):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        """
        self._patient_cohort = self._extract_incident_prevalent(
            self._extract_base_patient_cohort(
                limit_to_ukrdc=limit_to_ukrdc,
                limit_query_length=limit_query_length,
            )
        )

    def extract_satellite_stats(self, unit: str = "all") -> DialysisStats:
        """
        Returns:
            DialysisStats:
        """

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        pop_size = len(self._patient_cohort.ukrdcid.unique())

        return DialysisStats(
            metadata=DialysisMetadata(
                population=pop_size,
                from_time=self.time_window[0],
                to_time=self.time_window[1],
            ),
            all_patients_home_therapies=self._calculate_therapies_all_patients(
                subunit=unit
            ),
            incident_home_therapies=self._calculate_therapies_incident_patients(
                subunit=unit
            ),
            prevalent_home_therapies=self._calculate_therapies_prevalent_patients(
                subunit=unit
            ),
            incentre_dialysis_frequency=self._calculate_dialysis_frequency(
                subunit=unit
            ),
            incident_initial_access=self._calculate_access_incident(subunit=unit),
        )

    def extract_stats(
        self,
        limit_to_ukrdc: Optional[bool] = True,
        limit_query_length: Optional[int] = None,
    ) -> UnitLevelDialysisStats:
        """Extract all stats for the dialysis module
        Returns:
            DialysisStats: Dialysis statistics object
        """
        # If we don't already have a patient cohort, extract one

        if self._patient_cohort is None:
            self.extract_patient_cohort(
                limit_to_ukrdc=limit_to_ukrdc,
                limit_query_length=limit_query_length,
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
