"""
Tests/debug helpers designed to be run with a real database connection. We can
also use them for verification against known ukrdc data.
"""

from sqlalchemy.orm import Session 
from ukrdc_stats.calculators.dialysis import DialysisStatsCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator
import datetime as dt
import json


def test_krt_prevalent_cohort(ukrdc3_real_db_session:Session):
    
    ANNUAL_REPORT_2022 = {
        "RNJ00": {
            "prevalent_population": 2851,
            "pct_ichd": 40.6,
            "pct_pd": 8.1,
            "pct_hhd": 1.6,
            "pct_tx": 49.7
        },
        "RJZ": {
            "prevalent_population": 1394,
            "pct_ichd": 50.1,
            "pct_pd": 7.4,
            "pct_hhd": 2.8,
            "pct_tx": 39.7,
        },
        "RFBAK": {
            "prevalent_population": 2719,
            "pct_ichd": 38.1,
            "pct_pd": 5.5,
            "pct_hhd": 1.8,
            "pct_tx": 54.6
        },
        "RAJ": {
            "prevalent_population": 897,
            "pct_ichd": 48.6,
            "pct_pd": 9.1,
            "pct_hhd": 2.6,
            "pct_tx": 39.7
        }
    }
    
    renal_unit = "RJZ"
    
    if ukrdc3_real_db_session is not None:
        calculator = DialysisStatsCalculator(
            ukrdc3_real_db_session, 
            renal_unit, 
            from_time=dt.datetime(2020, 12, 31), 
            to_time=dt.datetime(2021, 12, 31)
        )

        dialysis_stats = calculator.extract_stats()
        #incident_patients = dialysis_stats.all.incident_krt.data
        #all_patients = dialysis_stats.all.all_treatments_krt
        

        # The annual report 2022 contains the following stats for Barts
        # prevalent population = 2,750 31/12/2021
        # 2,750 39.8 9.4 0.9 49.9
        report_data = ANNUAL_REPORT_2022[renal_unit]
        n_krt = report_data["prevalent_population"]
        pct_ichd = report_data["pct_ichd"]
        pct_pd = report_data["pct_pd"]
        pct_hhd = report_data["pct_hhd"]
        pct_tx = report_data["pct_tx"]
        
        n_tx = pct_tx * n_krt / 100.
        n_pd = n_krt* pct_pd / 100.
        n_ichd = n_krt * pct_ichd / 100.
        n_hhd = n_krt * pct_hhd / 100.

        prevalent_data = dialysis_stats.all.prevalent_krt
        prev_pop = prevalent_data.metadata.population_size
        #confidence = 0.05 
        confidence = 0.1
        assert (1 - confidence) * n_krt < prev_pop
        assert (1 + confidence) * n_krt > prev_pop

        prev_mod = dict(zip(prevalent_data.data.x, prevalent_data.data.y))
        print("    |ukrdc|annual")
        print(f"tx |{round(n_tx)}  " + str(prev_mod["TX"]))
        print(f"pd |{round(n_pd)}  " + str(prev_mod["PD"]))
        print(f"ichd |{round(n_ichd)}  " + str(prev_mod["HD In-centre"]))
        print(f"n_hhd |{round(n_hhd)}  " + str(prev_mod["HD Home"]))
        
        assert (1 - confidence) * n_tx < prev_mod["TX"]
        assert (1 + confidence) * n_tx > prev_mod["TX"]
        
        
        assert (1 - confidence) * n_pd < prev_mod["PD"]
        assert (1 + confidence) * n_pd > prev_mod["PD"]

        # for treatment entries without dialysis type we add them 
        assert (1 - confidence) * n_ichd < prev_mod["HD In-centre"] + prev_mod["HD Unknown/Incomplete"]
        assert (1 + confidence) * n_ichd > prev_mod["HD In-centre"] - prev_mod["HD Unknown/Incomplete"]
        
        assert (1 - confidence) * n_hhd < prev_mod["HD Home"] + prev_mod["HD Unknown/Incomplete"]
        assert (1 + confidence) * n_hhd > prev_mod["HD Home"] - prev_mod["HD Unknown/Incomplete"]

def test_krt_incident_cohort(ukrdc3_real_db_session:Session):
    ANNUAL_REPORT_2022 = {
        "RNJ00": {
            "incident_population": 293,
            "pct_ichd": 67.9,
            "pct_pd": 25.3,
            "pct_hhd": 0.0,
            "pct_tx": 6.8
        },
        "RJZ": {
            "incident_population": 203,
            "pct_ichd": 78.3,
            "pct_pd": 17.7,
            "pct_hhd": 0.0,
            "pct_tx": 3.9,
        },
        "RFBAK": {
            "incident_population": 342,
            "pct_ichd": 74.6,
            "pct_pd": 18.4,
            "pct_hhd": 0.0,
            "pct_tx": 7.0
        },
        "RAJ": {
            "incident_population": 169,
            "pct_ichd": 76.3,
            "pct_pd": 20.1,
            "pct_hhd": 0.0,
            "pct_tx": 3.6
        }
    }
    
    renal_unit = "RAJ"
    #renal_unit = "RNJ00"
    #renal_unit = "RJZ"
    #renal_unit = "RFBAK"
    if ukrdc3_real_db_session is not None:
        start = dt.datetime(2021, 12, 31)
        stop = dt.datetime(2022, 12, 31)
        calculator = DialysisStatsCalculator(
            ukrdc3_real_db_session, 
            renal_unit, 
            from_time=start, 
            to_time=stop
        )

        # the 2022 annual report shows the incident patients of 2022
        dialysis_stats = calculator.extract_stats()
        report = calculator.generate_cohort_report("incident")
        for row in report.table.rows:
            #if row[]
            if row[3] == "TX":
                print(f"'{row[0]}',")
            
        

        #cohort = cohort[cohort["incident"]]
        incident_data = dialysis_stats.all.incident_krt
        incident_pop = incident_data.metadata.population_size
        
        
        report_data = ANNUAL_REPORT_2022[renal_unit]
        n_krt = report_data["incident_population"]
        pct_ichd = report_data["pct_ichd"]
        pct_pd = report_data["pct_pd"]
        pct_hhd = report_data["pct_hhd"]
        pct_tx = report_data["pct_tx"]
        
        n_tx = pct_tx * n_krt / 100.
        n_pd = n_krt * pct_pd / 100.
        n_ichd = n_krt * pct_ichd / 100.
        n_hhd = n_krt * pct_hhd / 100.

        confidence = 0.1 
        #confidence = 0.1
        #assert (1 - confidence) * n_krt < incident_pop
        #assert (1 + confidence) * n_krt > incident_pop
        print(incident_pop)
        print(n_tx + n_pd + n_ichd + n_hhd)


        incident_mod = dict(zip(incident_data.data.x, incident_data.data.y))
        
        
        keys = incident_mod.keys()
        print("    |annual| ukrdc")
        if "TX" in keys:
            print(f"tx |{n_tx}  " + str(incident_mod["TX"]))
        if "PD" in keys:
            print(f"pd |{n_pd}  " + str(incident_mod["PD"]))
        if "HD In-centre" in keys:
            print(f"ichd |{n_ichd}  " + str(incident_mod["HD In-centre"]))
        if "HD Home" in keys:
            print(f"n_hhd |{n_hhd}  " + str(incident_mod["HD Home"]))

        # SEE BIG FAT TODO ON CALCULATE THERAPY TYPES!!!
        assert (1 - confidence) * n_tx < incident_mod["TX"]
        assert (1 + confidence) * n_tx > incident_mod["TX"]
        
        
        assert (1 - confidence) * n_pd < incident_mod["PD"]
        assert (1 + confidence) * n_pd > incident_mod["PD"]

        # for treatment entries without dialysis type we add them 
        assert (1 - confidence) * n_ichd < incident_mod["HD In-centre"] + incident_mod["HD Unknown/Incomplete"]
        assert (1 + confidence) * n_ichd > incident_mod["HD In-centre"] - incident_mod["HD Unknown/Incomplete"]
        
        assert (1 - confidence) * n_hhd < incident_mod["HD Home"] + incident_mod["HD Unknown/Incomplete"]
        assert (1 + confidence) * n_hhd > incident_mod["HD Home"] - incident_mod["HD Unknown/Incomplete"]

  


def test_demographics_base_cohort(ukrdc3_real_db_session:Session):
    if ukrdc3_real_db_session is not None:
        calculator = DemographicStatsCalculator(
            ukrdc3_real_db_session, 
            "RNJ00", 
            date=dt.datetime(2022, 12, 31)
        )
        demog_stats = calculator.extract_stats()
        age = demog_stats.age.data.dict()
        ethnic_group = demog_stats.ethnic_group.data.dict()
        gender = demog_stats.gender.data.dict()
        population = demog_stats.metadata.population

        formatted_output = demog_stats.dict()
