"""
This example script shows how to extract a CKD cohort using the dashboard
stats calculator to a csv file. 
"""

import datetime as dt
from pathlib import Path
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator

# connection to the database
server = "ukrdc_live"
ukrdc_conn = PostgresConnection(app = server, tunnel = True, via_app = True)
ukrdc_sessionmaker = ukrdc_conn.session_maker()

FULL_EXTRACT = False

# set parameters
facilities = ["RCSLB", "RAQ01"]  #"RAL01", "RAE05", "RFPFG"
#facilities = []
prevalence_point = dt.datetime(2025, 6, 30,0,0,0)
#prevalence_point = dt.datetime(2023, 12, 31,0,0,0)
#report_file_path = Path(r"Q:\UKRDC\Assessments\Phil_extracts\2025_07_15")
#report_file_path = Path(".do_not_commit")

with ukrdc_sessionmaker() as ukrdc_session:
    region_map = map_codes("RR1", "URTS_region", session)
    for facility in facilities:
        # initialise the required calculator and extract the cohort from the
        # database
        calculator = PrevalentCKDCalculator(
            session=ukrdc_session, 
            facility=facility, 
            prevalence_point=prevalence_point,
        )
        cohort = calculator.extract_patient_cohort(extract_all=FULL_EXTRACT)
        
        # generate a report from the extracted data
        population, report = calculator.produce_report(
            output_columns=[
                    "sendingfacility","birthtime", "deathtime", "fromtime",
                    "totime", "sex", "postcode", "ethnicgroupcode", 
                    "ethnicgroupdesc", "ukkaethnicity", "admitreasoncode",
                    "admitreasoncodestd", "admitreasondesc", "assessmentstart",
                    "assessmentend", "assessmenttypecode", "assessmenttypecodestd",
                    "assessmenttypecodedesc", "assessmentoutcomecode", 
                    "assessmentoutcomecodestd", "assessmentoutcomecodedesc", 
                    "serviceidcode_creat", "resultvalue_creat", 
                    "resultvalueunits_creat", "observationtime_creat", 
                    "serviceidcode_labegfr", "resultvalue_labegfr", 
                    "resultvalueunits_labegfr", "observationtime_labegfr",
                    "calculated_egfr", "externalid", "organization"
                ]
            )

        # output results
        if FULL_EXTRACT:
            output_path = report_file_path / Path(f"ckd_report_{facility}_{prevalence_point.strftime("%y_%m_%d")}_full_timeline.csv")
        else:
            output_path = report_file_path / Path(f"ckd_report_{facility}_{prevalence_point.strftime("%y_%m_%d")}.csv")
        metadata = f"""# CKD Assessment Report
# Renal Unit : {facility}
# Database Server : {server}
# Prevalence Point : {prevalence_point.strftime("%Y-%m-%d")}
# Date Run : {dt.datetime.now().strftime("%Y-%m-%d")}
"""
        
        report.to_csv(output_path, metadata=metadata)
        print(f"{population} CKD patients extracted to file {output_path}")
