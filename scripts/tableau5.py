from rr_connection_manager import PostgresConnection
from sqlalchemy import select
from ukrdc_sqla.ukrdc import Patient

import pandas as pd
import numpy as np
import datetime as dt
from dateutil.relativedelta import relativedelta

from ukrdc_stats.calculators.krt_JM import (
    KRTStatsCalculator,
)  # includes timeline_code 120 as a transplant patient
# from ukrdc_stats.calculators.krt import KRTStatsCalculator

# conn = PostgresConnection(app = "ukrdc_live", tunnel = True, via_app = True)
conn = PostgresConnection(app="ukrdc_staging", tunnel=True, via_app=True)
session = conn.session()

start = dt.datetime(2024, 10, 1)
end = dt.datetime(2025, 1, 1)

d = {
    "centre_code": ["RNJ00", "RAQ01", "RHW01", "RCSLB", "RK7CC", "RFBAK", "RH8"],
    "centre": [
        "Barts",
        "Lister",
        "Reading",
        "Nottingham",
        "Sheffield",
        "Leicester",
        "Exeter",
    ],
    "region": [
        "London",
        "East of England",
        "South East",
        "East Midlands",
        "Yorkshire & Humber",
        "East Midlands",
        "South West",
    ],
    "country": [
        "England",
        "England",
        "England",
        "England",
        "England",
        "England",
        "England",
    ],
}

units = pd.DataFrame(data=d)
main_centres = pd.read_csv("C:/Intel/main_centres.csv")
satellite_centres = pd.read_csv("C:/Intel/satellite_centres.csv")
tableaudf = (
    pd.DataFrame()
)  # composite dataframe of all the individual years / units / groups

facilities = units["centre_code"].to_list()
print(facilities)

# create dataframe of demographics once to add to each cohort as we make them
print("Making demographics dataframe (approx one minute)")
query = (
    select(Patient.pid, Patient.gender, Patient.ethnicgroupcode, Patient.birthtime)
    #    .where(
    #       PatientRecord.ukrdcid.in_(
    #            select(PatientRecord.ukrdcid).where(
    #            PatientRecord.sendingfacility == facility))
    #    )
)
demographics = pd.DataFrame(session.execute(query).all())

demographics["birthtime"] = pd.to_datetime(
    demographics["birthtime"], errors="coerce"
)  # oddly some non-dates in the birthtime crashes age calc

# not quite correct as this is age NOW not age in the particular quarter
demographics["age"] = round(
    ((pd.Timestamp("now") - demographics["birthtime"]).dt.days) / 365, 1
)

# categorise by age ranges
bins = [18, 25, 35, 45, 55, 65, 75, 85, 150]
labels = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", ">=85"]
demographics["agegroup"] = pd.cut(
    demographics["age"], bins=bins, labels=labels, right=False
).astype("object")

# recode sex 1 2 into Male Female
demographics.loc[demographics["gender"] == "1", "gender"] = "Male"
demographics.loc[demographics["gender"] == "2", "gender"] = "Female"
# Not quite correct as this recodes None as Other
demographics["gender"] = demographics["gender"].apply(
    lambda x: "Other" if x not in ["Male", "Female"] else x
)

# recode ethnicity
demographics.loc[
    demographics["ethnicgroupcode"].isin(["A", "B", "C"]), "ethnicgroupcode"
] = "White"
demographics.loc[
    demographics["ethnicgroupcode"].isin(["H", "J", "K", "L"]), "ethnicgroupcode"
] = "Asian"
demographics.loc[
    demographics["ethnicgroupcode"].isin(["M", "N", "P"]), "ethnicgroupcode"
] = "Black"
demographics.loc[demographics["ethnicgroupcode"].isin(["Z"]), "ethnicgroupcode"] = (
    "Unknown"
)
# Not quite correct as this recodes None as Other
demographics["ethnicgroupcode"] = demographics["ethnicgroupcode"].apply(
    lambda x: "Other" if x not in ["White", "Asian", "Black", "Unknown"] else x
)

# add IMD

print("Demographics dataframe complete")

for y in facilities:
    facility = y
    print(y)
    for x in range(4):
        print(x)
        calculator1 = KRTStatsCalculator(
            session=session, facility=facility, from_time=start, to_time=end
        )
        jfm1 = calculator1._extract_base_patient_cohort()
        jfm2 = calculator1._extract_incident_prevalent(jfm1)

        jfm2["year"] = start.strftime("%Y")  # append Year column with all same value
        jfm2["quarter"] = (start.month + 2) / 3  # append Quarter column with  same value
        jfm2["adultpaed"] = "Adult"  # append Adult column with all same value
        jfm2["incidprev"] = "Incident"  # append Incidence column with all same value
        jfm2["variable2"] = "Gender"
        jfm2["measure"] = "Demography"
        jfm2["option"] = "Number"
        jfm2.loc[jfm2["admitreasoncode"] == "120", "registry_code_type"] = (
            "TX"  # mend missing 120 in Leic
        )
        jfm2.loc[jfm2["registry_code_type"] == "TX", "registry_code_type"] = (
            "Transplant"  # recode for tableau
        )

        with_centre = pd.merge(
            jfm2, units, left_on="sendingfacility", right_on="centre_code", how="left"
        )

        with_satellite = pd.merge(
            with_centre,
            satellite_centres,
            left_on="healthcarefacilitycode",
            right_on="satellite_code",
            how="left",
        )

        with_demographics = pd.merge(with_satellite, demographics, on="pid", how="left")

        with_demographics["satellite_code"] = np.where(
            with_demographics["satellite_code"].isna(),
            with_demographics["centre_code"],
            with_demographics["satellite_code"],
        )  # Assign blank satellite code to main unit code
        with_demographics["satellite"] = np.where(
            with_demographics["satellite"].isna(),
            with_demographics["centre"],
            with_demographics["satellite"],
        )  # Assign blank satellite to main unitfacility

        # incidence
        with_demographics["incidprev"] = (
            "Incident"  # update incidprev = Incident with all same value
        )
        jfm3 = with_demographics[
            [
                "gender",
                "ethnicgroupcode",
                "agegroup",
                "variable2",
                "measure",
                "country",
                "region",
                "centre_code",
                "satellite_code",
                "satellite",
                "centre",
                "year",
                "option",
                "incidprev",
                "quarter",
                "adultpaed",
                "registry_code_type",
                "pid",
            ]
        ].loc[
            (with_demographics.first_treatment)
            & (with_demographics.incident)
            & (with_demographics["sendingfacility"] == facility)
            & (with_demographics["admissionsourcecode"].isnull())
        ]

        # gender
        jfm3["varable2"] = "Gender"
        jfm4 = jfm3.groupby(
            [
                "gender",
                "centre",
                "adultpaed",
                "registry_code_type",
                "country",
                "variable2",
                "measure",
                "centre_code",
                "satellite_code",
                "satellite",
                "year",
                "option",
                "incidprev",
                "quarter",
                "region",
            ],
            as_index=False,
        ).agg(value=("pid", "count"))
        jfm4.rename(
            columns={"gender": "variable"}, inplace=True
        )  # characteristics all in 'variable' column
        tableaudf = pd.concat([tableaudf, jfm4])
        print(jfm4)

        # ethnnicity
        jfm3["varable2"] = "Ethnicity"
        jfm4 = jfm3.groupby(
            [
                "ethnicgroupcode",
                "centre",
                "adultpaed",
                "registry_code_type",
                "country",
                "variable2",
                "measure",
                "centre_code",
                "satellite_code",
                "satellite",
                "year",
                "option",
                "incidprev",
                "quarter",
                "region",
            ],
            as_index=False,
        ).agg(value=("pid", "count"))
        jfm4.rename(
            columns={"ethnicgroupcode": "variable"}, inplace=True
        )  # characteristics all in 'variable' column
        tableaudf = pd.concat([tableaudf, jfm4])

        # agegroup
        jfm3["varable2"] = "Age"
        jfm4 = jfm3.groupby(
            [
                "agegroup",
                "centre",
                "adultpaed",
                "registry_code_type",
                "country",
                "variable2",
                "measure",
                "centre_code",
                "satellite_code",
                "satellite",
                "year",
                "option",
                "incidprev",
                "quarter",
                "region",
            ],
            as_index=False,
        ).agg(value=("pid", "count"))
        jfm4.rename(
            columns={"agegroup": "variable"}, inplace=True
        )  # characteristics all in 'variable' column
        tableaudf = pd.concat([tableaudf, jfm4])

        # prevalence
        with_demographics["incidprev"] = (
            "Prevalent"  # update incidprev = Prevalent with all same value
        )
        jfm3 = with_demographics[
            [
                "gender",
                "ethnicgroupcode",
                "agegroup",
                "variable2",
                "measure",
                "country",
                "region",
                "centre_code",
                "satellite_code",
                "satellite",
                "centre",
                "year",
                "option",
                "incidprev",
                "quarter",
                "adultpaed",
                "registry_code_type",
                "pid",
            ]
        ].loc[
            (with_demographics.first_treatment)
            & (with_demographics.prevalent)
            & (with_demographics["sendingfacility"] == facility)
        ]

        # gender
        jfm3["varable2"] = "Gender"
        jfm4 = jfm3.groupby(
            [
                "gender",
                "centre",
                "adultpaed",
                "registry_code_type",
                "country",
                "variable2",
                "measure",
                "centre_code",
                "satellite_code",
                "satellite",
                "year",
                "option",
                "incidprev",
                "quarter",
                "region",
            ],
            as_index=False,
        ).agg(value=("pid", "count"))
        jfm4.rename(
            columns={"gender": "variable"}, inplace=True
        )  # characteristics all in 'variable' column
        tableaudf = pd.concat([tableaudf, jfm4])

        # ethnnicity
        jfm3["varable2"] = "Ethnicity"
        jfm4 = jfm3.groupby(
            [
                "ethnicgroupcode",
                "centre",
                "adultpaed",
                "registry_code_type",
                "country",
                "variable2",
                "measure",
                "centre_code",
                "satellite_code",
                "satellite",
                "year",
                "option",
                "incidprev",
                "quarter",
                "region",
            ],
            as_index=False,
        ).agg(value=("pid", "count"))
        jfm4.rename(
            columns={"ethnicgroupcode": "variable"}, inplace=True
        )  # characteristics all in 'variable' column
        tableaudf = pd.concat([tableaudf, jfm4])

        # agegroup
        jfm3["varable2"] = "Age"
        jfm4 = jfm3.groupby(
            [
                "agegroup",
                "centre",
                "adultpaed",
                "registry_code_type",
                "country",
                "variable2",
                "measure",
                "centre_code",
                "satellite_code",
                "satellite",
                "year",
                "option",
                "incidprev",
                "quarter",
                "region",
            ],
            as_index=False,
        ).agg(value=("pid", "count"))
        jfm4.rename(
            columns={"agegroup": "variable"}, inplace=True
        )  # characteristics all in 'variable' column
        tableaudf = pd.concat([tableaudf, jfm4])

        start = start - relativedelta(months=3)
        end = end - relativedelta(months=3)

# print(tableaudf)
tableaudf.rename(columns={"registry_code_type": "dialtplt"}, inplace=True)
tableaudf.to_csv("C:/Intel/tableau4.csv", index=True)
