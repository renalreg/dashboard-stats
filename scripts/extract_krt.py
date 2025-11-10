"""
Simple demo of how to use the krt calculator to produce a report on the
demographics of a krt cohort.
"""

import datetime as dt
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.krt import KRTStatsCalculator

conn = PostgresConnection(app = "ukrdc_live", tunnel = True, via_app = True)
sessionmaker = conn.session_maker()

facility = "RAJ"
start = dt.datetime(2025,7,30)
end = dt.datetime(2025,10,28)

with sessionmaker() as session:
    calculator = KRTStatsCalculator(
        session=session, 
        facility=facility, from_time=start, to_time=end
    )
    calculator.extract_patient_cohort()
    calculator.append_demographics()
    
    pop, report = calculator.produce_report(
        output_columns = ["ukrdcid", "sendingfacility", "registry_code_type", "incident", "prevalent", "agerange", "ethnicity","gender"],
        include_ni = True    
    )
    report.to_csv(".do_not_commit/report.csv")