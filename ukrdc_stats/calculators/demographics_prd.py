"""
Patient demographics with primary renal diagnosis information 
"""

import warnings

import datetime as dt
from typing import Dict, Optional
from pydantic import Field

import pandas as pd
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import Patient, PatientRecord, RenalDiagnosis

from ukrdc_stats.calculators.abc import AbstractFacilityStatsCalculator
from ukrdc_stats.exceptions import NoCohortError
from ukrdc_stats.utils import age_from_dob, map_codes

from ukrdc_stats.descriptions import demographic_descriptions
#from ..code_groupings import ETHNIC_GROUP_MAP, GENDER_GROUP_MAP, PRD_CODE_MAP
from ukrdc_stats.models.base import JSONModel
from ukrdc_stats.models.maps import (
    DoubleLabelled3d,
    Basic3dMetadata,
    AxisLabel3d,
    DoubleLabelled3dData,
)

# NHS digital gender map
GENDER_GROUP_MAP = {"1": "Male", "2": "Female", "9": "Indeterminate", "X": "Unknown"}



class DemographicsMetadata(JSONModel):
    population: Optional[int] = Field(
        None, description="Population demographics are calculated from"
    )

class DemographicsStatsPRD(JSONModel):
    gender: DoubleLabelled3d = Field(..., description="Gender PRD demographic stats")
    ethnic_group: DoubleLabelled3d = Field(
        ..., description="Ethnic group PRD demographic stats"
    )
    age: DoubleLabelled3d = Field(..., description="Age PRD demographic stats")
    metadata: DemographicsMetadata = Field(
        ..., description="Metadata describing demographic stats"
    )

def _mapped_key(key: str) -> str:
    """Tiny convenience function to return a common mapped column name

    Args:
        key (str): Column to map

    Returns:
        str: Mapped column name
    """
    return f"{key}_mapped"

def _mapped_if_exists(df: pd.DataFrame, column: str) -> pd.Series:
    """
    Convenience function to return the mapped column if it exists,
    otherwise return the original column

    Args:
        df (pd.DataFrame): Input dataframe
        column (str): Column to return

    Returns:
        pd.Series: Mapped column if it exists, otherwise the original column
    """
    mapped_column: str = _mapped_key(column)
    if mapped_column in df.columns:
        return df[mapped_column]
    else:
        warnings.warn(
            f"Column {mapped_column} does not exist in dataframe, returning {column} instead"
        )
        return df[column]

def calculate_base_patient_histogram_3d(
    cohort: pd.DataFrame, group: str, code_map: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """Extract a histogram of the patient cohort, grouped by the given column
    Args:
        cohort (pd.DataFrame): Patient cohort
        group (str): Column to group bys
    Raises:
        NoCohortError: If the patient cohort is empty
    Returns:
        pd.DataFrame: Histogram dataframe of the patient cohort
    """

    if code_map:
        mapped_column = f"{group}_mapped"
        cohort[mapped_column] = cohort[group].map(code_map)

        histogram = (
            cohort[["ukrdcid", mapped_column, "PRD"]]
            .drop_duplicates()
            .groupby([mapped_column, "PRD"])
            .count()
            .reset_index()
        )

    else:
        histogram = (
            cohort[["ukrdcid", group, "PRD"]]
            .drop_duplicates()
            .groupby([group, "PRD"])
            .count()
            .reset_index()
        )

    return histogram.rename(columns={"ukrdcid": "Count"})

class RenalDiagnosisStatsCalculator(AbstractFacilityStatsCalculator):
    """Calculates the demographics information based on the personal information listed in the patient table"""

    def __init__(
        self, session: Session, facility: str, date: Optional[dt.datetime] = None
    ):
        """Initialises the PatientDemographicStats class and immediately runs the relevant query

        Args:
            session (SQLAlchemy session): Connection to database to calculate statistic from.
            facility (str): Facility to calculate the
            date (datetime, optional): Date to calculate at. Defaults to today.
        """
        super().__init__(session, facility)

        # Set the date to calculate at, defaulting to today
        self.date: dt.datetime = date or dt.datetime.today()

    def _extract_base_patient_cohort(
        self,
        include_tracing: Optional[bool] = False,
        include_incomplete_prd: Optional[bool] = True,
        limit_to_ukrdc: Optional[bool] = True,
        limit_query_length: Optional[int] = None,
    ) -> pd.DataFrame:
        """Main database queries to produce a dataframe containing the patient demographics
        for a specified Unit.

        Args:
            include_tracing (bool, optional): Switch to use tracing rec. Defaults to False.

        Returns:
            pd.DataFrame: _description_
        """

        # TODO: Add ability to filter on modality

        # select all patients who have a patientrecord sent from the facility
        patient_query = (
            select(
                PatientRecord.ukrdcid,
                Patient.gender,
                Patient.ethnic_group_code,
                RenalDiagnosis.diagnosis_code,
                RenalDiagnosis.diagnosis_code_std,
                Patient.birth_time,
                Patient.death_time,
            )  # type:ignore
            .join(PatientRecord, Patient.pid == PatientRecord.pid)  # type:ignore
            .join(RenalDiagnosis,RenalDiagnosis.pid==PatientRecord.pid, isouter=True)
            .where(
                and_(
                    PatientRecord.sendingfacility == self.facility,
                    or_(
                        Patient.death_time.is_(None), Patient.death_time > self.date
                    ),  # only calculate demographics for living patients
                )
            )
        )

        # limit stats to ukrdc
        if limit_to_ukrdc:
            patient_query = patient_query.where(PatientRecord.sendingextract == "UKRDC")

        # limit to patients with complete prd 
        if not include_incomplete_prd:
            patient_query = patient_query.where(RenalDiagnosis.diagnosis_code.is_not(None))

        # limit number of records returned (for benchmarking)
        if limit_query_length:
            patients = next(
                pd.read_sql(
                    patient_query, self.session.bind, chunksize=limit_query_length
                )
            )

        else:
            patients = pd.read_sql(patient_query, self.session.bind)

        if include_tracing:
            # look to see to find data that might exclude patients from statistics
            # TODO: I still think there is more nuance than this. What if a patient has
            # been discharged or moved abroad or any other reason that they might appear
            # but not have their death recorded.
            exclude_patients = (
                select(PatientRecord.ukrdcid)
                .join(Patient, Patient.pid == PatientRecord.pid)  # type:ignore
                .where(
                    and_(
                        # PatientRecord.sendingfacility == "TRACING",
                        PatientRecord.ukrdcid.in_(
                            patients[pd.isna(patients.deathtime)].ukrdcid
                        ),
                        Patient.death_time < self.date,
                    )
                )
            )

            exclude_patients_list = pd.read_sql(exclude_patients, self.session.bind)

            # filter out patients in the exclusion list
            patients = patients[~patients.ukrdcid.isin(exclude_patients_list.ukrdcid)]

        return patients.drop_duplicates()
    
    def _calculate_gender(self) -> DoubleLabelled3d:
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")        

        
        gender = calculate_base_patient_histogram_3d(self._patient_cohort, "gender",GENDER_GROUP_MAP)

        return DoubleLabelled3d(
            metadata=Basic3dMetadata(
                title = "PRD by Gender",
                summary = "Breakdown of patient primary renal diagnosis separated by gender",
                description = "",
                axis_titles=AxisLabel3d(
                    x="Gender", y="Primary Renal Diagnosis", z="No. of Patients"
                ), 
            ),
            data=DoubleLabelled3dData(
                x = _mapped_if_exists(gender, "gender").tolist(),
                y = gender.PRD.tolist(),
                z = gender.Count.tolist(),
            )
        )

    def _calculate_ethnic_group_code(self)->DoubleLabelled3d:
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")
        
        ethnic_group_map = map_codes("NHS_DATA_DICTIONARY","URTS_ETHNIC_GROUPING",self.session)
        ethnicity = calculate_base_patient_histogram_3d(self._patient_cohort, "ethnicgroupcode", ethnic_group_map)
        
        return DoubleLabelled3d(
            metadata=Basic3dMetadata(
                title = "PRD by Ethnicity",
                summary = "Breakdown of patient ethnic group codes",
                description = "",
                axis_titles=AxisLabel3d(
                    x="Ethnicity", y="Primary Renal Diagnosis", z="No. of Patients"
                ), 
            ),
            data=DoubleLabelled3dData(
                x = _mapped_if_exists(ethnicity, "ethnicgroupcode").tolist(),
                y = ethnicity.PRD.tolist(),
                z = ethnicity.Count.tolist(),
            )
        )
    
    def _calculate_age(self)->DoubleLabelled3d:
        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")
        
        # add column with ages and calculate histogram
        self._patient_cohort["age"] = self._patient_cohort["birthtime"][
            pd.isna(self._patient_cohort.deathtime)
        ].apply(lambda dob: age_from_dob(self.date, dob))
        age = calculate_base_patient_histogram_3d(self._patient_cohort, "age")

        return DoubleLabelled3d(
            metadata=Basic3dMetadata(
                title = "PRD by Age",
                summary = "Distribution of patient ages",
                description = "",
                axis_titles=AxisLabel3d(
                    x="Age", y="Primary Renal Diagnosis", z="No. of Patients"
                ), 
            ),
            data=DoubleLabelled3dData(
                x = age.age.tolist(),
                y = age.PRD.tolist(),
                z = age.Count.tolist(),
            )
        )        
        
    def extract_patient_cohort(
        self,
        include_tracing: Optional[bool] = False,
        limit_to_ukrdc: Optional[bool] = True,
        limit_query_length: Optional[int] = None,
        include_incomplete_prd: Optional[bool] = True,
    ):
        """
        Extract a complete patient cohort dataframe to be used in stats calculations
        include_tracing switch allows patient records created by nhs tracing to be searched
        for DoD.
        """
        
        self._patient_cohort = self._extract_base_patient_cohort(
            include_tracing=include_tracing,
            limit_to_ukrdc=limit_to_ukrdc,
            limit_query_length=limit_query_length,
            include_incomplete_prd=include_incomplete_prd
        )

        
        # get prd coding standards and map to diagnosis code
        prd_code_std = self._patient_cohort[~self._patient_cohort.diagnosiscodestd.isna()].diagnosiscodestd.unique()
        prd_code_map = {}
        for std in prd_code_std:
            prd_code_map.update(map_codes(std, "URTS_DIAGNOSIS_GROUPING", self.session))
        self._patient_cohort["PRD"] = self._patient_cohort["diagnosiscode"].replace(prd_code_map)
        self._patient_cohort.loc[self._patient_cohort.PRD.isna(), "PRD"] = "No PRD"

    def extract_stats(
            self,
            include_tracing: Optional[bool] = False,
            limit_to_ukrdc: Optional[bool] = True,
            limit_query_length: Optional[int] = None,
        )->DemographicsStatsPRD:
        
        # If we don't already have a patient cohort, extract one
        if self._patient_cohort is None:
            self.extract_patient_cohort(
                include_tracing=include_tracing,
                limit_to_ukrdc=limit_to_ukrdc,
                limit_query_length=limit_query_length,
            )

        if self._patient_cohort is None:
            raise NoCohortError("No patient cohort has been extracted")



        pop_size = len(self._patient_cohort[["ukrdcid"]].drop_duplicates())

        return DemographicsStatsPRD(
            metadata=DemographicsMetadata(population=pop_size),
            gender=self._calculate_gender(),
            ethnic_group=self._calculate_ethnic_group_code(),
            age=self._calculate_age()
        )

