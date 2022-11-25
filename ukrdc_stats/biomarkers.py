"""
Generates biomaker data for a list of patients.
The stats here are loosly based on the metrics of chapter 5 of the annual report.
"""

import datetime as dt
from typing import List, Union
import pandas as pd


from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import ResultItem, LabOrder, CauseOfDeath, Patient, Code
from ukrdc_stats.exceptions import NoCohortError
from .models.generic_2d import Labelled2d, Labelled2dMetadata, Labelled2dData
from pydantic import BaseModel


# pydantic classes for the api
class BiomarkerMetaData(BaseModel):
    title: str
    summary: str
    description: str
    data_axis_titles: List[str]


class BiomarkerData(BaseModel):
    timestamps: List[dt.datetime]
    testresult: List[Union[float, None]]
    orderid: List[str]
    resultid: List[str]


class PatientBiomarker(BaseModel):
    ukrdcid: str
    median_result: Union[float, None]
    most_recent_result: Union[float, None]
    data: BiomarkerData


class PatientBiomarkers(BaseModel):
    meta_data: BiomarkerMetaData
    patient_data: List[PatientBiomarker]


def produce_output(
    query_result: pd.DataFrame, meta_data: BiomarkerMetaData
) -> PatientBiomarkers:

    # There is quite a bit of junk in the results table so this statement turns them
    # into nans
    query_result.resultvalue = query_result.resultvalue.apply(
        pd.to_numeric, errors="coerce"
    )

    # initialise variable for output
    biomarkers = PatientBiomarkers(meta_data=meta_data, patient_data=[])

    for ukrdcid in query_result.ukrdcid.unique():
        test_data_slice = (
            query_result[query_result.ukrdcid == ukrdcid]
            .replace("", None)
            .sort_values("enteredon")
        )

        biomarker = PatientBiomarker(
            ukrdcid=ukrdcid,
            median_result=test_data_slice.resultvalue.median(),
            most_recent_result=test_data_slice.resultvalue.iloc[-1],
            data=BiomarkerData(
                timestamps=test_data_slice.enteredon.tolist(),
                testresult=test_data_slice.resultvalue.tolist(),
                orderid=test_data_slice.orderid.tolist(),
                resultid=test_data_slice.resultid.tolist(),
            ),
        )

        biomarkers.patient_data.append(biomarker)

    return biomarkers


def generic_biomarkers_query(
    start_time: dt.datetime,
    end_time: dt.datetime,
    patients: pd.DataFrame,
    service_codes: List,
    session: Session,
) -> pd.DataFrame:
    """Queries the database to return a set of test results of a specified type for a given set of patients over a given timewidow.

    Args:
        start_time (dt.datetime): start of window
        end_time (dt.datetime): end of window
        patients (pd.DataFrame): list of patient identifiers must contain both the pid and the ukrdcid
        service_codes (List): list of service codes specifing the type of test
        session (Session):

    Returns:
        pd.DataFrame: result of queary
    """

    generic_query = (
        select(
            LabOrder.pid,
            ResultItem.id.label("resultid"),
            ResultItem.value,
            ResultItem.service_id,
            LabOrder.entered_on,
            ResultItem.order_id,
        )
        .join(LabOrder, LabOrder.id == ResultItem.order_id)
        .where(
            and_(
                LabOrder.pid.in_(patients.pid.tolist()),
                ResultItem.service_id.in_(service_codes),
                LabOrder.entered_on > start_time,
                LabOrder.entered_on < end_time,
            )
        )
    )

    test_data = pd.read_sql(generic_query, session.bind)
    test_data_merged = test_data.merge(patients, "inner", on="pid")

    return test_data_merged


def urea_reduction_ratio(
    start_time: dt.datetime,
    end_time: dt.datetime,
    patient: pd.DataFrame,
    session: Session,
) -> PatientBiomarkers:
    """_summary_

    Args:
        start_time (dt.datetime): Start date to collect tests from
        end_time (dt.datetime): Start date to collect tests from
        patient (pd.DataFrame): Dataframe containing pids and ukrdcids of patients this can be generated with the dialysis stats module
        session (Session): ukrdc3 session

    Returns:
        pd.DataFrame: Urea reduction ratio results for the above parameters
    """

    # query database to get test results
    test_data_id_merged = generic_biomarkers_query(
        start_time=start_time,
        end_time=end_time,
        patients=patient,
        service_codes=["QBLG9"],
        session=session,
    )

    if test_data_id_merged is None:
        raise NoCohortError("No URR results extracted")

    return produce_output(
        test_data_id_merged,
        BiomarkerMetaData(
            title="Urea Reduction Ratio",
            summary="",
            description="",
            data_axis_titles=["Date", "URR", "Order ID", "Test ID"],
        ),
    )


def haemoglobin(
    start_time: dt.datetime,
    end_time: dt.datetime,
    patient: pd.DataFrame,
    session: Session,
):

    # query haemoglobin
    test_data_id_merged = generic_biomarkers_query(
        start_time=start_time,
        end_time=end_time,
        patients=patient,
        service_codes=["QBLE1", "QBLEB"],
        session=session,
    )

    # ensure units match up
    test_data_id_merged.resultvalue.apply(pd.to_numeric, errors="coerce")
    test_data_id_merged[test_data_id_merged.serviceidcode == "QBLE1"].resultvalue = (
        test_data_id_merged[test_data_id_merged.serviceidcode == "QBLE1"].resultvalue
        * 10.0
    )

    return produce_output(
        test_data_id_merged,
        BiomarkerMetaData(
            title="Haemoglobin",
            summary="",
            description="",
            data_axis_titles=["Date", "Haemoglobin", "Order ID", "Test ID"],
        ),
    )


def cause_of_death(
    start_time: dt.datetime,
    end_time: dt.datetime,
    patient: pd.DataFrame,
    session: Session,
):

    # query cause of death
    query_cod = (
        select(
            Patient.death_time,
            CauseOfDeath.pid,
            CauseOfDeath.diagnosis_code,
            CauseOfDeath.diagnosis_code_std,
            Code.description.label("cause_of_death"),
        )
        .join(Patient, Patient.pid == CauseOfDeath.pid)
        .join(
            Code,
            and_(
                Code.coding_standard == CauseOfDeath.diagnosis_code_std,
                Code.code == CauseOfDeath.diagnosis_code,
            ),
        )
        .where(
            and_(
                CauseOfDeath.pid.in_(patient.pid.tolist()),
                Patient.death_time > start_time,
                Patient.death_time < end_time,
            )
        )
    )

    # merge tests with ukrdcids
    death_data = pd.read_sql(query_cod, session.bind)
    test_data_id_merged = death_data.merge(patient, "inner", on="pid")

    # turn into histogram
    test_data_hist = (
        test_data_id_merged[["ukrdcid", "cause_of_death"]]
        .drop_duplicates()
        .groupby(["cause_of_death"])
        .count()
        .reset_index()
    )

    return Labelled2d(
        metadata=Labelled2dMetadata(
            title="Cause of Death",
            summary="",
            description="",
            coding_standard_x="EDTA_COD",
        ),
        data=Labelled2dData(
            x=list(test_data_hist.cause_of_death), y=list(test_data_hist.ukrdcid)
        ),
    )
