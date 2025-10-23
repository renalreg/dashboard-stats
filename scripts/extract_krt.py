import datetime as dt
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.krt import KRTStatsCalculator

conn = PostgresConnection(app = "ukrdc_staging", tunnel = True, via_app = True)
sessionmaker = conn.session_maker()




#facility = "RCSLB"
facility = "RJZ"
start = dt.datetime(2024, 1, 1)
end = dt.datetime.now()


with sessionmaker() as session:
    calculator = KRTStatsCalculator(
        session=session, 
        facility=facility, from_time=start, to_time=end)

    calculator.extract_stats()
    report = calculator.generate_cohort_report(cohort="incident", include_ni=True)

    report.table.to_csv("report.csv")