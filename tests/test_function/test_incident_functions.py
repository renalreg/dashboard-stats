import datetime as dt

import pandas as pd

from ukrdc_stats.cohorts.base import _clean_equal_records


def test_clean_equal_records():
    """Example of the kind of duplicated record which results in two
    sendingfacilies sending the same treatment record"""

    infinity = dt.datetime(2200, 1, 1)
    cohort = pd.DataFrame(
        {
            "pid": [100000000, 200000000],
            "ukrdcid": [111111111, 111111111],
            "sendingfacility": ["RFDOG", "RFCAT"],
            "healthcarefacilitycode": ["RFDOG", "RFCAT"],
            "admitreasoncode": ["20", "20"],
            "admitreasoncodestd": ["CF_RR7_TREATMENT", "CF_RR7_TREATMENT"],
            "admissionsourcecode": [None, None],
            "admissionsourcecodestd": [None, None],
            "qbl05": [None, None],
            "hdp04": [None, None],
            "dischargereasoncode": [None, "38"],
            "dischargereasoncodestd": [None, "CF_RR7_DISCHARGE"],
            "dischargelocationcode": [None, "RFDOG"],
            "dischargelocationcodestd": [None, "ODS"],
            "registry_code_type": ["TX", "TX"],
            "end_of_care": ["0", "0"],
            "acute": ["0", "0"],
            "transfer_in": ["0", "0"],
            "deathtime": [infinity, infinity],
            "birthtime": [dt.datetime(1983, 9, 13, 1), dt.datetime(1983, 9, 13, 1)],
            "fromtime": [dt.datetime(2024, 2, 13), dt.datetime(2024, 2, 13)],
            "totime": [infinity, infinity],
            "ckd_centre": [None, "RFCAT"],
            "historic_tx": [False, False],
            "dialtplt": ["TX", "TX"],
            "timeline_order": [0, 1],
            "prev_fromtime": [pd.NaT, dt.datetime(2024, 2, 13)],
            "prev_totime": [pd.NaT, infinity],
            "prev_treatment_relationship": [None, "equals"],
            "timeline_start": [dt.datetime(2024, 2, 13), dt.datetime(2024, 2, 13)],
            "timeline_stop": [infinity, infinity],
        }
    )
    cohort["timeline_length"] = cohort["timeline_stop"] - cohort["timeline_start"]
    cohort["length_of_life"] = cohort["deathtime"] - cohort["timeline_start"]

    cleaned = _clean_equal_records(cohort)

    # only the row matching the ckd centre survives
    assert len(cleaned) == 1
    kept = cleaned.iloc[0]
    assert kept["pid"] == 200000000
    assert kept["sendingfacility"] == "RFCAT"
    # relationship recoded from the dropped previous record (which had none)
    assert pd.isna(kept["prev_treatment_relationship"])