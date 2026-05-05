"""This is a manual test to check the totals calculated by the calculator 
functions against know totals from UKKA published ckd demographics data.
"""
from ukrdc_stats.cohorts.base import krt_incident
from ukrdc_stats.utils.database import get_sessionmaker
from ukrdc_stats.utils.query import pid_ni_map
import datetime as dt
import pandas as pd
from dotenv import dotenv_values
from pathlib import Path





FACILITIES = [
# live
"RAJ",   # MSE
"RAQ01", # Lister
"RCSLB", # Nottingham
"RH8",   # RD&E
"RHW01", # Reading
"RK7CC", # Sheffield
"RL403", # Wolverhampton
"RNJ00", # Barts
"RFPFG", # Derby
"RBD01", # Dorset
"RLZ01", # Shrewsbury
"RP5",   # Doncaster
"BHLY",  # BHLY
]
#FACILITIES = ["RCSLB"]

SERVER = "ukrdc_live"
YEAR = 2024

config = dotenv_values(".env")
KEYPATH = config.get("UKRDC_STATS_KEYPATH")

rr_incident_data = Path(f".do_not_commit/rr_unaggregated/{YEAR}_full_incident_cohort.csv")
rr_ref_data = pd.read_csv(rr_incident_data)

if not KEYPATH:
    raise RuntimeError(
        "Missing UKRDC_STATS_KEYPATH. Set it in your environment or in a .env file."
    )
    
start_date = dt.datetime(YEAR-1, 12, 31)
end_date = dt.datetime(YEAR, 12, 31)

with get_sessionmaker(SERVER, keypath=KEYPATH)() as session:
    incident_patients = []
    ni_map = pid_ni_map(session, FACILITIES)
    for facility in FACILITIES:
        incident_cohort = krt_incident(session, facility, start_date=start_date, end_date=end_date)
        
        # try to map join nhs number
        incident_cohort = incident_cohort.merge(ni_map[["pid", "patientid"]][ni_map.organization == "NHS"], on="pid", how="left")
        incident_cohort.rename(columns = {"patientid": "nhs_number"}, inplace=True)

        # try to map join chi
        incident_cohort = incident_cohort.merge(ni_map[["pid", "patientid"]][ni_map.organization == "CHI"], on="pid", how="left")
        incident_cohort.rename(columns = {"patientid": "chi"}, inplace=True)

        # try to map join hsc
        incident_cohort = incident_cohort.merge(ni_map[["pid", "patientid"]][ni_map.organization == "HSC"], on="pid", how="left")
        incident_cohort.rename(columns = {"patientid": "hsc"}, inplace=True)

        incident_cohort["nhsno"] = incident_cohort["nhs_number"].fillna(incident_cohort["chi"]).fillna(incident_cohort["hsc"])         
        incident_patients.append(incident_cohort[["ukrdcid", "pid", "centre_code", "satellite_code", "dialtplt", "timeline_start", "nhsno"]])

    incident_all = pd.concat(incident_patients)
    incident_all = incident_all.merge(rr_ref_data[["nhsno", "KRT-start", "centre", "trtstart"]], on="nhsno", how="left")
    

    # Prepare output dataframes
    # Sheet 1: Patients where trtstart is NA (prevalent)
    not_incident = incident_all[incident_all["trtstart"].isna()].sort_values(["centre_code", "satellite_code", "nhsno"])
    
    # Sheet 2: Patients with different modality (dialtplt != trtstart)
    different_modalities = incident_all[
        incident_all["trtstart"].notna() & (incident_all["dialtplt"] != incident_all["trtstart"])
    ].sort_values(["centre_code", "satellite_code", "nhsno"])
    
    # Sheet 3: Patients with different treatment centre (centre_code != centre)
    different_treatment_centre = incident_all[
        incident_all["centre"].notna() & (incident_all["centre_code"] != incident_all["centre"])
    ].sort_values(["centre_code", "satellite_code", "nhsno"])

    # Sheet 4: Patients in reference dataset but not in calculated dataset (undetected incidence)
    rr_ref_facilities = rr_ref_data[rr_ref_data["centre"].isin(FACILITIES)]
    undetected_incidence = rr_ref_facilities[~rr_ref_facilities["nhsno"].isin(incident_all["nhsno"])].sort_values(["centre", "nhsno"])
    
    
    # Write to Excel with multiple sheets
    with pd.ExcelWriter(f".do_not_commit/incident_comparison_{YEAR}.xlsx", engine="openpyxl") as writer:
        not_incident.to_excel(writer, sheet_name="not incident", index=False)
        different_modalities.to_excel(writer, sheet_name="different modalities", index=False)
        different_treatment_centre.to_excel(writer, sheet_name="different treatment centre", index=False)
        undetected_incidence.to_excel(writer, sheet_name="undetected incidence", index=False)


    

#    pid_map = pid_ni_map(session, FACILITIES)
#    pid_map = pid_map[pid_map.organization.isin(["NHS", "CHI", "HSC"])]
#    rr_ref_data = rr_ref_data.merge(pid_map, left_on="NHSno", right_on="patientid", how="left")
#    rr_ref_data = rr_ref_data[["pid", "NHSno", "KRT-start", "centre", "trt-start"]]
    
    

#    incident_cohort = incident_cohort.merge(rr_ref_data, left_on="pid", right_on="pid", how="left").sort_values("dialtplt")
    
    print(":)")

    
#    centre_cohort = krt_incident(session, FACILITY, start_date=dt.datetime(2023, 1, 1), end_date=dt.datetime(2023, 12, 31))
#    centre_cohort = centre_cohort[centre_cohort["centre_code"] == FACILITY]
