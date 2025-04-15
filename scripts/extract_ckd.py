"""
This example script shows how to extract a CKD cohort using the dashboard
stats calculator to a csv file. 
"""



import datetime as dt
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator

# connection to the database
ukrdc_conn = PostgresConnection(app = "ukrdc_live", tunnel = True, via_app = True)
ukrdc_sessionmaker = ukrdc_conn.session_maker()


# set parameters
facility = "RCSLB"
#facility = "RAQ01" 
prevalence_point = dt.datetime(2023, 12, 31,0,0,0)
report_file_path = f"Q:/UKRDC/Assessments/Phil_extracts/ckd_report_{facility}.csv"

with ukrdc_sessionmaker() as ukrdc_session:
    # initialise the required calculator and extract the cohort from the
    # database
    calculator = PrevalentCKDCalculator(
        session=ukrdc_session, 
        facility=facility, 
        prevalence_point=prevalence_point,
    )
    cohort = calculator.extract_patient_cohort()
    
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
    report.to_csv(report_file_path)
    print(f"{population} CKD patients extracted to file {report_file_path}")
