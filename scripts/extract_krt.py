import datetime as dt
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.krt import KRTStatsCalculator

conn = PostgresConnection(app = "ukrdc_staging", tunnel = True, via_app = True)
sessionmaker = conn.session_maker()




facility = "RKB01"
#facility = "RNJ00"
#start = dt.datetime(2025, 7, 26)
#start = dt.datetime(2025,1,1)
#end = start + dt.timedelta(days = 90)



end = dt.datetime.now()
start = end - dt.timedelta(days = 90)

with sessionmaker() as session:
    calculator = KRTStatsCalculator(
        session=session, 
        facility=facility, from_time=start, to_time=end)

    calculator.extract_stats()
    report = calculator.generate_cohort_report(cohort="incident", include_ni=False)

    report.table.to_csv(".do_not_commit/report.csv")