import pandas as pd
from pandas import Timestamp

# data to create _patient_cohort dataframe from (and to check the functions which query the database against)
DIALYSIS_COHORT_DATA = {
    "ukrdcid": [
        "ID_test:0",
        "ID_test:1",
        "ID_test:2",
        "ID_test:3",
        "ID_test:4",
        "ID_test:5",
        "ID_test:6",
        "ID_test:7",
        "ID_test:8",
        "ID_test:9",
    ],
    "sendingextract": [
        "UKRDC",
        "UKRDC",
        "UKRDC",
        "UKRDC",
        "UKRDC",
        "UKRDC",
        "UKRDC",
        "UKRDC",
        "UKRDC",
        "UKRDC",
    ],
    "pid": [
        "test:0",
        "test:1",
        "test:2",
        "test:3",
        "test:4",
        "test:5",
        "test:6",
        "test:7",
        "test:8",
        "test:9",
    ],
    "healthcarefacilitycode": [
        "RFPUS",
        "RFPUS",
        "RFPUS",
        "RFPUS",
        "RFPUS",
        "RFPUS",
        "RFPUS",
        "RFPUS",
        "RFPUS",
        "RFPUS",
    ],
    "admitreasoncode": ['51', '4', '51', '201', '56', '201', '242', '54', '45', '201'],
    "registry_code_type": ['PD', 'HD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'HD', 'PD'],
    "qbl05": [None, None, None, None, None, None, None, None, None, None],
    "hdp04": [None, None, None, None, None, None, None, None, None, None],
    "fromtime": [Timestamp('2018-12-15 00:00:00'), Timestamp('2018-12-15 00:00:00'), Timestamp('2018-12-15 00:00:00'), Timestamp('2018-12-15 00:00:00'), Timestamp('2018-12-01 00:00:00'), Timestamp('2018-12-15 00:00:00'), Timestamp('2018-12-15 00:00:00'), Timestamp('2018-12-15 00:00:00'), Timestamp('2018-12-15 00:00:00'), Timestamp('2018-12-15 00:00:00')],
    "totime": [Timestamp('2019-12-01 00:00:00'), Timestamp('2019-12-01 00:00:00'), Timestamp('2019-12-01 00:00:00'), Timestamp('2019-12-01 00:00:00'), Timestamp('2019-12-15 00:00:00'), Timestamp('2019-12-01 00:00:00'), Timestamp('2019-12-15 00:00:00'), Timestamp('2019-12-01 00:00:00'), Timestamp('2019-12-01 00:00:00'), Timestamp('2019-12-01 00:00:00')],
    "deathtime": [None, None, None, None, None, None, None, None, None, None],
    "dischargereasoncode": [None, None, None, None, None, None, None, None, None, None],
    "firsttreatment": [True, True, True, True, True, True, True, True, True, True],
    "lasttreatment" : [True, True, True, True, True, True, True, True, True, True]
}

ETHNICITY_GROUP_CODES = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "J",
    "K",
    "L",
    "M",
    "N",
    "P",
    "R",
    "S",
    "Z",
    "99",
]

QHD20_CODES = ["TLN", "NLN", "AVF"]

QBL05_CODES = ["HOSP", "HOME"]

# incident prevalent data for the dialysis calculator tests
DIALYSIS_INCIDENT_PREVALENT = {
    "prevalent": [False, False, False, False, True, False, True, False, False, False],
    "incident": [True, True, True, True, False, True, True, True, True, True],
}

# data to populate lookup table
MODALITY_CODES = {
    "registry_code": ['1', '10', '11', '111', '12', '121', '13', '14', '15', '16', '162', '17', '181', '182', '183', '19', '2', '201', '202', '203', '241', '242', '243', '3', '4', '41', '42', '43', '44', '45', '49', '5', '50', '51', '52', '53', '54', '55', '56', '57', '59', '81', '82', '83', '9'],
    "registry_code_desc" : ['HAEMODIALYSIS', 'CAPD STANDARD', 'CAPD DISCONNECT', 'ASSISTED CAPD', 'CYCLINGPD>=6 NIGHTS/WK DRY', 'ASSISTED APD', 'CYCLINGPD<6 NIGHTS/WK DRY', 'CYCLING >+6 NIGHTS/WK WET', 'CYCLING PD<6 NIGHTS/WK WET', 'ASSISTED CYCLING PD >= 6 NIGHTS/WK DRY', 'TRANSFER IN ON : ASSISTED APD', 'ASSISTED CYCLING PD >= 6 NIGHTS/WK DRY (DAY DWELL)', 'Tfr in on: Acute haemodialysis - ARF', 'Tfr in on: Acute haemofiltration - ARF', 'Trf in on: Acute peritoneal dialysis - ARF', 'PERITONEAL DIALYSIS-TYPE UNKNO', 'HAEMOFILTRATION', 'HYBRID CAPD WITH HD', 'HYBRID APD WITH HD', 'HYBRID APD WITH CAPD', 'TRANSFER IN ON : HYBRID CAPD WITH HD', 'TRANSFER IN ON : HYBRID APD WITH HD', 'TRANSFER IN ON : HYBRID APD WITH CAPD', 'HAEMODIAFILTRATION', 'HAEMODIALYSIS>4 DAYS PER WEEK', 'TFR: HAEMODIALYSIS', 'TFR: HAEMOFILTRATION', 'TFR: HAEMODIAFILTRATION', 'XFR IN:HAEMO > 4 DAYS/WK', 'Transfer in on : Ultrafiltration', 'TFR:HAEMODIALYSIS-TYPE UNKNOWN', 'ULTRAFILTRATION', 'TFR: CAPD STANDARD', 'TFR: CAPD DISCONNECT', 'TFR:CYCLINGPD>6NIGHTS/WK DRY', 'TFR: CYCLINGPD<6 NIGHT/WK DRY', 'TFR: CYCLINGPD>=6 NIGHT/WK WET', 'TFR: CYCLINGPD<6 NIGHT/WK WET', 'Transfer in on : Assisted Cycling PD >= 6 nights/wk dry', 'Transfer in on : Assisted Cycling PD >= 6 nights/wk wet (day dwell)', 'TFR:PERITONEAL DIALYSIS-UNKNOW', 'Acute haemodialysis - ARF', 'Acute haemofiltration - ARF', 'Acute PD - ARF', 'HAEMODIALYSIS - TYPE UNKNOWN'],
    "registry_code_type" : ['HD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'HD', 'HD', 'PD', 'PD', 'HD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'HD', 'HD', 'HD', 'HD', 'HD', 'HD', 'HD', 'HD', 'HD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'PD', 'HD', 'HD', 'PD', 'HD'],
    "acute" : ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '1', '1', '1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '1', '1', '1', '0'],
    "transfer_in" : ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '1', '0', '1', '1', '1', '0', '0', '0', '0', '0', '1', '1', '1', '0', '0', '1', '1', '1', '1', '1', '1', '0', '1', '1', '1', '1', '1', '1', '1', '1', '1', '0', '0', '0', '0'],
    "ckd" : ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
    "cons": ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
    "rrt": ['1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '0', '0', '0', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '0', '0', '0', '1'],
    "end_of_care": ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
    "is_imprecise": ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '1']
}

