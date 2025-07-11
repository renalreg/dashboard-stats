import os
from rr_connection_manager import PostgresConnection
from sqlalchemy import select
from ukrdc_sqla.ukrdc import Patient

import pandas as pd
import numpy as np
import datetime as dt
from dateutil.relativedelta import relativedelta

from ukrdc_stats.calculators.krt import (
    KRTStatsCalculator,
)  # includes timeline_code 120 as a transplant patient
# from ukrdc_stats.calculators.krt import KRTStatsCalculator

from ukrdc_sqla.ukrdc import CodeMap

# conn = PostgresConnection(app = "ukrdc_live", tunnel = True, via_app = True)
# Establish connection to UKRDC
conn = PostgresConnection(app="ukrdc_staging", tunnel=True, via_app=True)
session = conn.session()

START_DATE = dt.datetime(2024, 10, 1)
END_DATE = dt.datetime(2025, 1, 1)

OUTPUT_DIR = ".do_not_commit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Columns by which the data is grouped
GROUP_COLUMNS = [
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
                "region"]

# Relevant columns from the dataset
DATASET_COLUMNS = [
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

data = {
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

# Create a dataframe of units
units = pd.DataFrame(data=data)

# Load centres and satellites from csv files
satellite_centres = pd.read_csv("C:/Intel/satellite_centres.csv")

# Create empty dataframe to store all the individual years / units / groups results
tableaudf = pd.DataFrame() 

# Get a separate list of facilities ("centre_code" in the units dataframe)
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

# Convert birthtimes into a DateTime object, making them easier to work with
# If the input is an invalid date for some reason (e.g., formating) - set it to NaT (Not a Time)
demographics["birthtime"] = pd.to_datetime(
    demographics["birthtime"], errors="coerce"
) 

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

# Recode gender 1/2 into Male Female using dictionary
demographics["gender"] = demographics["gender"].replace({
    "1": "Male",
    "2": "Female"
})
# Recode gender that is not NaN or in ["Male", "Female"] into "Other"
demographics["gender"] = demographics["gender"].apply(
    lambda x: x if pd.isna(x) or x in ["Male", "Female"] else "Other"
)

# Recode ethnicity using CodeMap table
# First, get source_code and destination_code from the database
query = select(CodeMap.source_code, CodeMap.destination_code).where(CodeMap.destination_coding_standard == "URTS_ETHNIC_GROUPING")
ethnicity_map = pd.DataFrame(session.execute(query).all())

# Then merge the map with the dataset
demographics = demographics.merge(
    ethnicity_map,
    how="left",
    left_on="ethnicgroupcode",
    right_on="source_code"
)

# Finally, cleanup the dataset by renaming "destination_code" into a "ethnicgroupcode"
demographics = demographics.drop(columns=["ethnicgroupcode", "source_code"])
demographics = demographics.rename(columns={"destination_code": "ethnicgroupcode"})

# Recode ethnicities that are not NaN or in ["White", "Asian", "Black", "Unknown"] as "Other"
demographics["ethnicgroupcode"] = demographics["ethnicgroupcode"].apply(
    lambda x: x if pd.isna(x) or x in ["White", "Asian", "Black", "Unknown"] else "Other"
)

# add IMD

print("Demographics dataframe complete")

# Iterate through all facilities one by one
for facility in facilities:
    print(facility)
    # Iterate through 4 quarters backwards (i.e., start at Q4, then Q3 etc.)
    for x in range(4):
        print(x)
        
        # Create an instance of a KRT Calculator object - it's responsible for extracting cohort
        calculator1 = KRTStatsCalculator(
            session=session, facility=facility, from_time=START_DATE, to_time=START_DATE
        )
        
        # Extract base patient cohort
        jfm1 = calculator1._extract_base_patient_cohort()
        # Pass the patient cohort to _extract_incident_prevalent function to add incident/prevalence data to it
        print(facility, x)
        jfm2 = calculator1._extract_incident_prevalent(jfm1)

        # Calculate date columns based on START_DATE
        jfm2["year"] = START_DATE.strftime("%Y")  # append Year column with all same value
        jfm2["quarter"] = (START_DATE.month + 2) / 3  # append Quarter column with  same value
        
        # Hardcode some of the metadata
        jfm2["adultpaed"] = "Adult"  # append Adult column with all same value
        jfm2["incidprev"] = "Incident"  # append Incidence column with all same value
        jfm2["variable2"] = "Gender"
        jfm2["measure"] = "Demography"
        jfm2["option"] = "Number"
        
        # Assign "TX" to the registry_code_type only for patients where admitreasoncode == "120"
        jfm2.loc[jfm2["admitreasoncode"] == "120", "registry_code_type"] = (
            "TX"  # mend missing 120 in Leic
        )
        
        # Assign "Transplant" to the registry_code_type only for patients where registry_code_type == "TX"
        jfm2.loc[jfm2["registry_code_type"] == "TX", "registry_code_type"] = (
            "Transplant"  # recode for tableau
        )

        # Merge patient cohort with the units dataframe
        with_centre = pd.merge(
            jfm2, units, left_on="sendingfacility", right_on="centre_code", how="left"
        )

        # Merge cohort with the satelite dataframe 
        with_satellite = pd.merge(
            with_centre,
            satellite_centres,
            left_on="healthcarefacilitycode",
            right_on="satellite_code",
            how="left",
        )

        # Merge cohort with the demographics data
        with_demographics = pd.merge(with_satellite, demographics, on="pid", how="left")

        # If "satellite_code" is not specified, set "satellite_code" to "centre_code", else keep it "satellite_code"
        with_demographics["satellite_code"] = np.where(
            with_demographics["satellite_code"].isna(),
            with_demographics["centre_code"],
            with_demographics["satellite_code"],
        ) 
        
        # If "satellite" is not specified, set "satellite" to "centre", else keep it "satellite"
        with_demographics["satellite"] = np.where(
            with_demographics["satellite"].isna(),
            with_demographics["centre"],
            with_demographics["satellite"],
        ) 

        # Hardcode "incideprev" with "Incident" value
        with_demographics["incidprev"] = (
            "Incident"
        )
        
        # Select only relevant columns from the dataset
        jfm3 = with_demographics[DATASET_COLUMNS].loc[ # Filter for rows where all of the following is true:
            (with_demographics.first_treatment) # This is first treatment
            & (with_demographics.incident) # This is an incident
            & (with_demographics["sendingfacility"] == facility) # Sending facility matches
            & (with_demographics["admissionsourcecode"].isnull()) # Admission source is not specified
        ]

        # Group by gender (keeping all the other data)
        jfm3["variable2"] = "Gender"
        jfm4 = jfm3.groupby(GROUP_COLUMNS,
            as_index=False,
        ).agg(value=("pid", "count")) # Count how many rows in each group
        jfm4.rename(
            columns={"gender": "variable"}, inplace=True 
        ) # Rename "gender" column into "variable", so that columns are the same across all groups
        # Add the gender grouping to the results dataframe 
        tableaudf = pd.concat([tableaudf, jfm4])
        print(jfm4.head(5)) # Print first 5 rows of the dataframe

        # Group by ethncity (keeping all the other data)
        jfm3["variable2"] = "Ethnicity"
        jfm4 = jfm3.groupby(["ethnicgroupcode"] + GROUP_COLUMNS,
            as_index=False,
        ).agg(value=("pid", "count")) # Count how many rows in each group
        jfm4.rename(
            columns={"ethnicgroupcode": "variable"}, inplace=True 
        ) # Rename "ethnicgroupcode" column into "variable"
        # Add the ethnicity grouping to the results dataframe 
        tableaudf = pd.concat([tableaudf, jfm4])

        # Group by agegroup (keeping all the other data)
        jfm3["variable2"] = "Age"
        jfm4 = jfm3.groupby(["agegroup"] + GROUP_COLUMNS,
            as_index=False,
        ).agg(value=("pid", "count")) # Count how many rows in each group
        jfm4.rename(
            columns={"agegroup": "variable"}, inplace=True
        )  # Rename "agegroup" column into "variable"
        # Add the agegroup grouping to the results dataframe 
        tableaudf = pd.concat([tableaudf, jfm4])

        # prevalence
        with_demographics["incidprev"] = (
            "Prevalent"  # update incidprev = Prevalent with all same value
        )
        # Select only relevant columns from the dataset
        jfm3 = with_demographics[
            DATASET_COLUMNS
        ].loc[ # Filter for rows where all of the following is true:
            (with_demographics.first_treatment) # This is first treatment
            & (with_demographics.prevalent) # This is prevalent case
            & (with_demographics["sendingfacility"] == facility) # Facility matches
        ]

        # Group by gender (keeping all the other data)
        jfm3["variable2"] = "Gender"
        jfm4 = jfm3.groupby(["gender"] + GROUP_COLUMNS,
            as_index=False,
        ).agg(value=("pid", "count")) # Count how many rows in each group
        jfm4.rename(
            columns={"gender": "variable"}, inplace=True
        )  # Rename "gender" column into "variable"
        # Add the gender grouping to the results dataframe 
        tableaudf = pd.concat([tableaudf, jfm4])

        # Group by ethnicity (keeping all the other data)
        jfm3["variable2"] = "Ethnicity"
        jfm4 = jfm3.groupby(["ethnicgroupcode"] + GROUP_COLUMNS,
            as_index=False,
        ).agg(value=("pid", "count")) # Count how many rows in each group
        jfm4.rename(
            columns={"ethnicgroupcode": "variable"}, inplace=True
        )  # Rename "ethnicgroupcode" column into "variable"
        # Add the ethnicity grouping to the results dataframe 
        tableaudf = pd.concat([tableaudf, jfm4])

        # Group by agegroup (keeping all the other data)
        jfm3["variable2"] = "Age"
        jfm4 = jfm3.groupby(["agegroup"] + GROUP_COLUMNS,
            as_index=False,
        ).agg(value=("pid", "count")) # Count how many rows in each group
        jfm4.rename(
            columns={"agegroup": "variable"}, inplace=True
        )  # Rename "agegroup" column into "variable"
        # Add the age grouping to the results dataframe 
        tableaudf = pd.concat([tableaudf, jfm4])

        # Reduce start and end date by 3 to go to the previous quarter
        START_DATE = START_DATE - relativedelta(months=3)
        END_DATE = END_DATE - relativedelta(months=3)

# Close database connection
session.close()

# print(tableaudf)
tableaudf.rename(columns={"registry_code_type": "dialtplt"}, inplace=True)

# Save dataframe to the OUTPUT_DIR location
tableaudf.to_csv(os.path.join(OUTPUT_DIR, "tableau4.csv"), index=True)
