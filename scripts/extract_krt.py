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
end = dt.datetime(2025,11,17)
start = end - dt.timedelta(days=30)

with sessionmaker() as session:
    calculator = KRTStatsCalculator(
        session=session, 
        facility=facility, from_time=start, to_time=end
    )

    # get aggregated stats
    stats = calculator.extract_stats()
    calculator.append_demographics()
    
    print("\nPrevalent Modalities:")
    prevalent_patients = zip(stats.all.prevalent_krt.data.x, stats.all.prevalent_krt.data.y)
    for x, y in prevalent_patients:
        print(f"{x}: {y}")
    print("total = ", stats.all.prevalent_krt.metadata.population_size)


    hd_patients = zip(stats.all.incident_krt.data.x, stats.all.incident_krt.data.y)
    print("\nIncident Modalities:")
    for x, y in hd_patients:
        print(f"{x}: {y}")
    print("total = ", stats.all.incident_krt.metadata.population_size)

    access_data = zip(stats.all.incident_initial_access.data.x, stats.all.incident_initial_access.data.y)
    print("\nAccess Data:")
    total = 0
    for x, y in access_data:
        print(f"{x}: {y}")
        total += y
    print("total = ", total)

    pop, report = calculator.produce_report(
        output_columns = [
            "ukrdcid", 
            "sendingfacility", 
            "registry_code_type", 
            "incident", 
            "prevalent", 
            "agerange", 
            "ethnicity", 
            "gender"
        ],
        include_ni = True    
    )
    report.to_csv(".do_not_commit/report.csv")