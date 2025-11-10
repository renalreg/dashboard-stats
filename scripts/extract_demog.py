import datetime as dt
from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator

conn = PostgresConnection(app = "ukrdc_live", tunnel = True, via_app = True)
sessionmaker = conn.session_maker()




facility = "RAJ"
#facility = "RNJ00"
#start = dt.datetime(2025, 7, 26)
start = dt.datetime(2025,7,30)
end = dt.datetime(2025,10,28)
#end = start + dt.timedelta(days = 90)

# Statistics calculated from 30/07/2025, 16:02 to 28/10/2025, 16:02

#end = dt.datetime.now()
#start = end - dt.timedelta(days = 90)

with sessionmaker() as session:
    calculator = DemographicStatsCalculator(
        session=session, 
        facility = facility
    )
    calculator.extract_stats()
    #report = calculator.generate_report()

    #report.table.to_csv(".do_not_commit/report.csv")