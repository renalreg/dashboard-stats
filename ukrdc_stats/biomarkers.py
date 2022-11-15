"""
Generates biomaker data for a list of patients.
The stats here are loosly based on the metrics of chapter 5 of the annual report.
"""

import datetime as dt
from typing import List
import pandas as pd
import numpy as np

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import ResultItem, LabOrder, CauseOfDeath, Patient, Code


from pydantic import BaseModel
from .models.generic_2d import (
    Labelled2dMetadata,
    Labelled2dData,
    TimeSeries2dData,
    Basic2dMetadata,
    AxisLabels2d,
    Labelled2d,
)

# pydantic class to assemble urea reduction rates
class URR(BaseModel):
    ukrdcid: str
    median_urr: float
    urr: TimeSeries2dData


class URRStats(BaseModel):
    meta_data: Basic2dMetadata
    data: List[URR]


#'' for cause of death


def urea_reduction_ratio(
    start_time: dt.datetime,
    end_time: dt.datetime,
    patient: pd.DataFrame,
    session: Session,
) -> URRStats:
    """_summary_

    Args:
        start_time (dt.datetime): Start date to collect tests from
        end_time (dt.datetime): Start date to collect tests from
        patient (pd.DataFrame): Dataframe containing pids and ukrdcids of patients this can be generated with the dialysis stats module
        session (Session): ukrdc3 session

    Returns:
        pd.DataFrame: Urea reduction ratio results for the above parameters
    """

    # query database to get the test results
    query_biomarkers = (
        select(
            LabOrder.pid, ResultItem.service_id, ResultItem.value, LabOrder.entered_on
        )
        .join(LabOrder, LabOrder.id == ResultItem.order_id)
        .where(
            and_(
                LabOrder.pid.in_(patient.pid.tolist()),
                or_(ResultItem.service_id == "QBLG9"),
                LabOrder.entered_on > start_time,
                LabOrder.entered_on < end_time,
            )
        )
    )

    # merge tests with ukrdcids
    test_data = pd.read_sql(query_biomarkers, session.bind)
    test_data_id_merged = test_data.merge(patient, "inner", on="pid")

    # assemble pydantic object for api to return
    urr_items = []
    urr_median = []
    for ukrdcid in test_data_id_merged.ukrdcid.unique():
        test_data_slice = (
            test_data_id_merged[test_data_id_merged.ukrdcid == ukrdcid]
            .replace("", None)
            .sort_values("enteredon")
        )

        urr_median.append(test_data_slice.resultvalue.median())

        urr_items.append(
            URR(
                ukrdcid=ukrdcid,
                median_urr=urr_median[-1],
                urr=TimeSeries2dData(
                    x=test_data_slice.enteredon.tolist(),
                    y=test_data_slice.resultvalue.astype(float).tolist(),
                ),
            )
        )

    # order items by ascending median URR
    urr_items_sorted = [urr_items[index] for index in np.argsort(urr_median)]

    return URRStats(
        meta_data=Basic2dMetadata(
            title="Patient Urea Reduction Ratio",
            axis_titles=AxisLabels2d(x="Test Date", y="Urea Reduction Ratio (%)"),
        ),
        data=urr_items_sorted,
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
            title="Cause of Death", coding_standard_x="EDTA_COD"
        ),
        data=Labelled2dData(
            x=list(test_data_hist.cause_of_death), y=list(test_data_hist.ukrdcid)
        ),
    )
