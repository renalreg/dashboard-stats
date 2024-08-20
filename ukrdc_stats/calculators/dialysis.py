"""
Patient cohort dialysis stats calculator
"""

import datetime as dt


from typing import Optional, Tuple, List, Dict

import pandas as pd
from sqlalchemy import and_, func, or_, select, cast
from sqlalchemy.orm import Session
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
    cohort: str
    population:int
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
    mappings = {
        "HOSP": "In-centre",
        "SATL": "In-centre",
        "HOME": "Home"
    }
    
    # Update 'qbl05' based on conditions
    patient_cohort.loc[patient_cohort.registry_code_type.isin(["PD", "TX"]), "qbl05"] = ""
    patient_cohort.loc[(patient_cohort.registry_code_type == "HD") & patient_cohort.qbl05.isna(), "qbl05"] = "Unknown/Incomplete"
    patient_cohort.loc[:, "qbl05"] = patient_cohort["qbl05"].replace(mappings)


    most_recent_treatments = patient_cohort[patient_cohort["most_recent"] == True][["pid", "registry_code_type", "qbl05"]].drop_duplicates()

    # Group and count patients by 'registry_code_type' and 'qbl05'
    grouped_patients = (
        most_recent_treatments
        .groupby(["registry_code_type", "qbl05"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("registry_code_type")
    )

    # Create labels and patients lists
    labels = [f"{row.registry_code_type} {row.qbl05}".strip() for _, row in grouped_patients.iterrows()]
    patients = grouped_patients["count"].tolist()

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
        if to_time > dt.datetime.now() - dt.timedelta(days=90):
            raise Exception("cannot calculate stats within 90 of today")

        super().__init__(session, facility)

        # Create a precisely 2 element time window tuple
        self.time_window: Tuple[dt.datetime, dt.datetime] = (from_time, to_time)

        # defines encoding of KRT treatment types
        self.registry_code_types: List[str] = ["HD", "PD", "TX"]
        self.home_therapy_code_types: List[str] = ["HOSP", "SATL", "INCENTRE"]

    def extract_patient_cohort(
        self,
        limit_to_ukrdc: Optional[bool] = True
    ):
        """
        Extract a complete patient cohort dataframe. This is calculated fresh
        each time but we would probably want to implement some caching here.
        """
        self._patient_cohort = self._extract_incident_prevalent(
            self._extract_base_patient_cohort(
                limit_to_ukrdc=limit_to_ukrdc
            ) 
        )

    def _extract_base_patient_cohort(
        self,
        limit_to_ukrdc: Optional[bool] = True,
    ) -> pd.DataFrame:
        """Extract a base patient cohort dataframe from the database
        Returns:
            pd.DataFrame: Patient cohort dataframe
        """

        query = (
            select(
                PatientRecord.pid,
                Treatment.healthcarefacilitycode,
                Treatment.admitreasoncode,
                Treatment.admitreasoncodestd,
                Treatment.qbl05,
                Treatment.hdp04,
                Treatment.dischargereasoncode,
                Treatment.dischargelocationcodestd,
                ModalityCodes.acute,
                ModalityCodes.registry_code_type,
                Patient.deathtime,
                Treatment.fromtime,
                Treatment.totime,   
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
                or_(Patient.deathtime > self.time_window[0], Patient.deathtime.is_(None)),
                PatientRecord.sendingfacility == self.facility,
            )
        )

        if limit_to_ukrdc:
            query = query.where(PatientRecord.sendingextract == "UKRDC")

        # Create dataframe
        base_cohort = pd.DataFrame(self.session.execute(query)).drop_duplicates()
        
        # pandas by default tries to be helpful and create compound keys
        # we don't want this for now
        base_cohort = base_cohort.reset_index(drop=True)
        
        #run function to link each treatment to the one that follows
        base_cohort = self._chain_treatments(base_cohort)

        # Exclude "acute" patients and records post or prior to recoveries
        base_cohort = self._exclude_records(base_cohort)

        # identify the records with the most recent from time for each pid 
        most_recent = base_cohort[base_cohort["fromtime"] < self.time_window[1]].reset_index(drop=True)
        most_recent = most_recent.groupby("pid", as_index=False)["fromtime"].max()
        
        # Merge with the original cohort to identify the most recent treatments
        base_cohort = base_cohort.merge(most_recent, on=["pid"], how="left", suffixes=("", "_max"))
        base_cohort["most_recent"] = base_cohort["fromtime"] == base_cohort["fromtime_max"]

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

        # The possibility of overlapping records means the nextfromtime needs
        # some complex adjusting. The aim of this is to ensure that the
        # next_fromtime is always describing a gap in the treatment timeline
        def adjust_next_fromtime(group):
            # skip any single record group
            group = group.reset_index(drop=True)
            if len(group) > 1:
                for i in range(len(group) - 1):
                    if pd.isna(group.loc[i, "next_fromtime"]):
                        continue

                    # We have an overlap when next fromtime is less than the
                    # too time
                    if group.at[i, "next_fromtime"] < group.at[i, "totime"]:
                        # loop through following records and adjust based on
                        # relative end of records
                        for j in range(i + 1, len(group)):
                            # if overlapping record ends transfer and blank its
                            # next fromtime
                            # debug
                            if pd.isna(group.at[j, "next_fromtime"]):
                                continue

                            if group.at[j, "totime"] < group.at[i, "totime"]:
                                next_value = group.at[j, "next_fromtime"]
                                group.at[i, "next_fromtime"] = next_value
                                group.at[j, "next_fromtime"] = pd.NaT
                            else:
                                # Otherwise we blank the first records fromtime
                                group.at[i, "next_fromtime"] = pd.NaT
                                break
            return group

        raw_patients = raw_patients.groupby("pid", as_index=False).apply(adjust_next_fromtime)

        return raw_patients

    def _exclude_records(self, base_cohort: pd.DataFrame):
        """This implements any conditions the might cause a patient to be removed from
        the cohort. For example anyone who is in a 90 recovery period which spans the
        end of the time window should be excluded. Any patient with treatment modality
        code which implies CKD that dies before the end of the window will also be
        excluded.
        """

        # recovery window
        recoveries = ((base_cohort["next_fromtime"] - base_cohort["totime"]) > dt.timedelta(days=90))
        patient_recoveries = base_cohort[recoveries][["pid","next_fromtime", "totime"]]
        
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


    def _extract_incident_prevalent(self, base_cohort: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a base cohort from _extract_base_patient_cohort and extracts the incident and prevalent patients.
        This is currently a draft version and probably needs careful reviewing.
        Args:
            base_cohort (pd.DataFrame): Base cohort from output of _extract_base_patient_cohort
        Returns:
            pd.DataFrame: Patient cohort dataframe
        """

        # we calculate the beginning and end of each continuous/uninterrupted treatment period
        base_cohort['timeline_start'] = base_cohort.groupby('pid', as_index= False)['fromtime'].transform('min')
        base_cohort['timeline_stop'] = base_cohort.groupby('pid', as_index= False)['totime'].transform('max')
        base_cohort['timeline_length'] = base_cohort['timeline_stop'] -  base_cohort['timeline_start']
        base_cohort['life_length'] = base_cohort['deathtime'] - base_cohort['timeline_start']

        # patients might change from acute to chronic so we need to ensure 1-1
        # relationship between patient and acute/chronic status. If a patient
        # starts as acute and is recoded as chronic they should be treated as
        # chronic from the point they come under the care of the renal unit
        ckd_pids = base_cohort["pid"][base_cohort["acute"] == '0'].drop_duplicates()
        base_cohort["is_ckd"] = base_cohort["pid"].isin(ckd_pids)

        # prevalent cohort includes everyone who's treatment block spans the end of the time window 
        # who is not acute. Acute patients must meet the same criterion with the addition of being
        # on KRT for more than 90 days. 
        base_cohort["prevalent"] = (
            (base_cohort['timeline_start'] < self.time_window[1]) 
            & ((base_cohort['timeline_stop'] > self.time_window[1]) | base_cohort['timeline_stop'].isna())
            # patients on 
            & ~((base_cohort['is_ckd'] == False) & (base_cohort['timeline_length'] < dt.timedelta(days=90)))
        )

        # patients not coded as acute
        base_cohort["incident"] = (
            (base_cohort['timeline_start'] > self.time_window[0]) 
            & ( 
                (base_cohort['timeline_length'] > dt.timedelta(days=90)) | base_cohort['timeline_length'].isna())
                | (base_cohort["is_ckd"] & (base_cohort["life_length"] < dt.timedelta(days=90)))
        )

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
                func.sum(cast(DialysisSession.qhd31, Float))
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
            session_data["freq"] = pd.Series(dtype='float64')

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

        initial_access_data = pd.DataFrame(self.session.execute(initial_access_query)).drop_duplicates()
        
        if len(initial_access_data)>0:
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
            data=Labelled2dData(
                x=x_data, y=y_data
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
                self._patient_cohort.incident & self._patient_cohort.most_recent
            ]
        else:
            incident_cohort = self._patient_cohort[
                self._patient_cohort.incident
                & (self._patient_cohort.healthcarefacilitycode == subunit)
                & self._patient_cohort.most_recent
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
        #pop_size = None
        #pop_size = len(self._patient_cohort.ukrdcid.unique())


        return DialysisStats(
            metadata=DialysisMetadata(
                population=pop_size,
                from_time=self.time_window[0],
                to_time=self.time_window[1],
            ),
            all_treatments_krt=self._calculate_therapies_all_patients(
                subunit=unit
            ),
            incident_krt=self._calculate_therapies_incident_patients(
                subunit=unit
            ),
            prevalent_krt=self._calculate_therapies_prevalent_patients(
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
            all=self.extract_satellite_stats(), 
            units=unit_stats
        )
    
    def generate_cohort_report(self, cohort:str)->BaseTable:
        if cohort == "incident": 
            table = self.produce_report(
                ["incident", "most_recent"],
                ["pid", "admitreasoncode", "admitreasoncodestd", "registry_code_type"]
            )
        
        if cohort == "prevalent":
            table = self.produce_report(
                ["incident", "most_recent"],
                ["pid", "admitreasoncode", "admitreasoncodestd", "registry_code_type"]
            )

        return CohortReport(
            cohort=cohort, 
            population = 0, 
            table = table
        )
        

        #if cohort == "all_treatments":
        #    self.generate_report()