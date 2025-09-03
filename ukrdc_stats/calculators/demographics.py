"""
Patient cohort demographics stats calculator
"""

import datetime as dt
from typing import Optional
from pydantic import Field

import pandas as pd
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import (
    Patient,
    PatientRecord,
    Treatment,
    ResultItem,
    Observation,
)

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError
from ukrdc_stats.utils import (
    age_from_dob,
    map_codes,
    _calculate_base_patient_histogram,
    _mapped_if_exists,
    _get_satellite_list,
)

from ukrdc_stats.descriptions import demographic_descriptions
from ukrdc_stats.models.base import JSONModel
from ukrdc_stats.models.generic_2d import (
    AxisLabels2d,
    Labelled2d,
    Labelled2dData,
    Labelled2dMetadata,
)

# NHS digital gender map
GENDER_GROUP_MAP = {"1": "Male", "2": "Female", "9": "Indeterminate", "X": "Unknown"}


class DemographicsMetadata(JSONModel):
    population: Optional[int] = Field(
        None, description="Population demographics are calculated from"
    )


class DemographicsStats(JSONModel):
    gender: Labelled2d = Field(..., description="Gender demographic stats")
    ethnic_group: Labelled2d = Field(
        ...,
        description="Ethnicity Histogram based on the 5 ethnicity groupings used in the annual report",
    )
    age: Labelled2d = Field(..., description="Age statistics of living patients")
    metadata: DemographicsMetadata = Field(
        ..., description="Metadata describing demographic stats"
    )


class DemographicStatsCalculator(AbstractFacilityStatsCalculator):
    """Calculates the demographics information based on the personal information listed in the patient table"""

    def __init__(
        self,
        session: Session,
        facility: str,
        date: Optional[dt.datetime] = None,
        end_date: Optional[dt.datetime] = None,
        start_date: Optional[dt.datetime] = None,
    ):
        """Initialises the PatientDemographicStats class and immediately runs the relevant query

        Args:
            session (SQLAlchemy session): Connection to database to calculate statistic from.
            facility (str): Facility to calculate the
            date (datetime, optional): Date to calculate at. Defaults to today.
        """
        super().__init__(session, facility)

        # Set the dates to calculate between, defaulting to today and 90 days ago
        self.end_date: dt.datetime = date or end_date or dt.datetime.today()
        self.start_date: dt.datetime = start_date or self.end_date - dt.timedelta(
            days=90
        )

    def _extract_base_patient_cohort(
        self,
        include_tracing: Optional[bool] = True,
        limit_to_ukrdc: Optional[bool] = True,
        ukrr_expanded: Optional[bool] = False,
    ) -> pd.DataFrame:
        """Main database queries to produce a dataframe containing the patient demographics
        for a specified Unit.

        Args:
            include_tracing (bool, optional): Switch to use tracing rec. Defaults to False.

        Returns:
            pd.DataFrame: _description_
        """

        sats = _get_satellite_list(self.facility, self.session)

        # the following reflect criteria which are applied to the ukrr
        # quarterly extract process (i.e the criteria used to load data into
        # the renalregistry database). See here for more information:
        # https://github.com/renalreg/ukrr_quarterly_extract/blob/ec65cc06858cdabaa379e9e18b8f0614fc2c9af2/ukrr_extract/extract_functions.py#L342

        if ukrr_expanded:
            ukkr_cohort_query = (
                select(Treatment.pid)
                .distinct()
                .where(
                    or_(
                        and_(
                            Treatment.fromtime < self.start_date,
                            or_(
                                Treatment.healthcarefacilitycode.in_(sats),
                                Treatment.healthcarefacilitycode.in_(self.facility),
                            ),
                            or_(
                                Treatment.totime >= self.end_date,
                                Treatment.totime.is_(None),
                            ),
                        ),
                        and_(
                            ResultItem.observation_time < self.start_date,  # pylint: disable=C0121
                            ResultItem.observation_time >= self.end_date,
                        ),
                        and_(
                            Observation.observation_time < self.start_date,  # pylint: disable=C0121
                            Observation.observation_time >= self.end_date,
                        ),
                    )
                )
            )
        else:
            ukkr_cohort_query = (
                select(Treatment.pid)
                .distinct()
                .where(
                    Treatment.fromtime < self.end_date,
                    or_(
                        Treatment.healthcarefacilitycode.in_(sats),
                        Treatment.healthcarefacilitycode == self.facility,
                    ),
                    or_(
                        Treatment.totime >= self.end_date,
                        Treatment.totime.is_(None),
                    ),
                )
            )

        # select all patients who have a patientrecord sent from the facility
        patient_query = (
            select(
                PatientRecord.ukrdcid,
                Patient.gender,
                Patient.ethnic_group_code,
                Patient.birth_time,
                Patient.death_time,
            )
            .join(PatientRecord, Patient.pid == PatientRecord.pid)
            .where(
                PatientRecord.sendingfacility == self.facility,
                PatientRecord.pid.in_(ukkr_cohort_query),
            )
        )

        # limit stats to ukrdc
        if limit_to_ukrdc:
            patient_query = patient_query.where(PatientRecord.sendingextract == "UKRDC")

        # extract patient cohort
        patients = pd.DataFrame(self.session.execute(patient_query)).drop_duplicates()
        if patients.empty:
            raise NoCohortError(
                f"No patient cohort has been extracted. Facility {self.facility} may not have a UKRDC feed."
            )

        if include_tracing:
            # Can we trace deathtime by crosslinking records in the ukrdc?
            exclude_patients = (
                select(PatientRecord.ukrdcid)
                .join(Patient, Patient.pid == PatientRecord.pid)  # type:ignore
                .where(
                    and_(
                        # PatientRecord.sendingfacility == "TRACING",
                        PatientRecord.ukrdcid.in_(
                            patients[pd.isna(patients.death_time)].ukrdcid
                        ),
                        Patient.death_time < self.end_date,
                    )
                )
            )

            exclude_patients_list = pd.DataFrame(
                self.session.execute(exclude_patients)
            ).drop_duplicates()

            # filter out patients in the exclusion list
            patients = patients[~patients.ukrdcid.isin(exclude_patients_list.ukrdcid)]

        return patients.drop_duplicates()

    def _calculate_gender(self) -> Labelled2d:
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        gender = _calculate_base_patient_histogram(
            self._patient_cohort, "gender", GENDER_GROUP_MAP
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Gender Distribution",
                summary="Breakdown of patient gender identity codes",
                description=demographic_descriptions["GENDER_DESCRIPTION"],
                axis_titles=AxisLabels2d(x="Gender", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=_mapped_if_exists(gender, "gender").tolist(), y=gender.Count.tolist()
            ),
        )

    def _calculate_ethnic_group_code(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        ethnic_group_map = map_codes(
            "NHS_DATA_DICTIONARY", "URTS_ETHNIC_GROUPING", self.session
        )

        ethnic_group_code = _calculate_base_patient_histogram(
            self._patient_cohort, "ethnic_group_code", ethnic_group_map
        )

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Ethnic Group",
                summary="Breakdown of patient ethnic group codes",
                description=demographic_descriptions["ETHNIC_GROUP_DESCRIPTION"],
                axis_titles=AxisLabels2d(x="Ethnicity", y="No. of Patients"),
            ),
            data=Labelled2dData(
                x=_mapped_if_exists(ethnic_group_code, "ethnic_group_code").tolist(),
                y=ethnic_group_code.Count.tolist(),
            ),
        )

    def _calculate_age(self):
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")

        # add column with ages and calculate histogram
        # self._patient_cohort["age"] = self._patient_cohort["birth_time"][
        #    self._patient_cohort.death_time.isna()
        # ].apply(lambda dob: age_from_dob(self.end_date, dob))
        self._patient_cohort["age"] = self._patient_cohort["birth_time"].apply(
            lambda dob: age_from_dob(self.end_date, dob)
        )
        age = _calculate_base_patient_histogram(self._patient_cohort, "age")

        return Labelled2d(
            metadata=Labelled2dMetadata(
                title="Age Distribution",
                summary="Distribution of patient ages",
                description=demographic_descriptions["AGE_DESCRIPTION"],
                axis_titles=AxisLabels2d(x="Age", y="No. of Patients"),
            ),
            data=Labelled2dData(x=age.age.tolist(), y=age.Count.tolist()),
        )

    def extract_patient_cohort(
        self,
        include_tracing: Optional[bool] = False,
        limit_to_ukrdc: Optional[bool] = True,
        ukrr_expanded: Optional[bool] = False,
    ):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        include_tracing switch allows patient records created by nhs tracing to be searched
        for DoD.
        """
        self._patient_cohort = self._extract_base_patient_cohort(
            include_tracing=include_tracing,
            limit_to_ukrdc=limit_to_ukrdc,
            ukrr_expanded=ukrr_expanded,
        )

    def extract_stats(
        self,
        include_tracing: Optional[bool] = False,
        limit_to_ukrdc: Optional[bool] = True,
        ukrr_expanded: Optional[bool] = False,
    ) -> DemographicsStats:
        """Extract all stats for the demographics module

        Returns:
            DemographicsStats: Demographics statistics object
        """
        # If we don't already have a patient cohort, extract one
        if self._patient_cohort is None:
            self.extract_patient_cohort(
                include_tracing=include_tracing,
                limit_to_ukrdc=limit_to_ukrdc,
                ukrr_expanded=ukrr_expanded,
            )

        if self._patient_cohort is None:
            raise NoCohortError(
                f"No patient cohort has been extracted. Facility {self.facility} may not have a UKRDC feed."
            )

        pop_size = len(self._patient_cohort[["ukrdcid"]].drop_duplicates())

        # Build output object
        return DemographicsStats(
            metadata=DemographicsMetadata(population=pop_size),
            ethnic_group=self._calculate_ethnic_group_code(),
            gender=self._calculate_gender(),
            age=self._calculate_age(),
        )
