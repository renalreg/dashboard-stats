import datetime as dt
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.ckd import PrevalentCKDCalculator

ukrdc_conn = PostgresConnection(app = "ukrdc_live", tunnel = True, via_app = True)
ukrdc_sessionmaker = ukrdc_conn.session_maker()

archive_conn = PostgresConnection(app = "ukrdc_live", tunnel = True, via_app = True)
archive_conn._connection_details["db_name"] = "removed_xml_archive"
archive_sessionmaker = archive_conn.session_maker()

facility = "RCSLB"
prevalence_point = dt.datetime.now()

with ukrdc_sessionmaker() as ukrdc_session:
    with archive_sessionmaker() as archive_session:
        calculator = PrevalentCKDCalculator(
            session=ukrdc_session, 
            facility=facility, 
            prevalence_point=prevalence_point,
            v5_archive_session=archive_session
    )
        cohort = calculator.extract_patient_cohort() 
        
        print(":)")


    