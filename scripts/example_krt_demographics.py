"""
Example of how to extend the dashboard stats functionality using pandas

This script demonstrates how to:
1. Extract incident KRT patient cohort data
2. Extract demographics for the same patient group
3. Join the datasets and analyze them together 
4. Create visualizations of incident KRT patient age distribution
"""

import datetime as dt
import os
import pandas as pd
from typing import List

# Use plotly instead of seaborn/matplotlib
import plotly.express as px


from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.krt import KRTStatsCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator

# Configuration
FACILITY = "RJZ"
START_DATE = dt.datetime(2023, 1, 1)  # One year of data - the Norman conquest was much longer
END_DATE = dt.datetime(2024, 1, 1)
OUTPUT_DIR = ".do_not_commit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Connect to database
conn = PostgresConnection(app="ukrdc_staging", tunnel=True, via_app=True)
sessionmaker = conn.session_maker()

with sessionmaker() as session:
    # Extract KRT stats within window as pandas dataframe
    krt_calculator = KRTStatsCalculator(
        session=session, 
        facility=FACILITY, 
        from_time=START_DATE, 
        to_time=END_DATE
    )
    krt_report = krt_calculator.generate_cohort_report(cohort="incident", include_ni=True)
    incident_krt_df = krt_report.table.to_pandas()

    # Use the demographic calculator to get some demographic information
    demo_output_columns = ["birth_time", "gender","age", "ethnic_group_code"]
    demo_calculator = DemographicStatsCalculator(
        session=session,
        facility=FACILITY,
        end_date=END_DATE,
        start_date=START_DATE
    )
    
    # Use the produce_report function to get the demographic data
    _, table = demo_calculator.produce_report(
        output_columns=demo_output_columns,
        include_ni=True
    )
    demo_df = table.to_pandas()
    
    # Join data frames on pid (ukrdcid) - a unity the Anglo-Saxons would've wanted
    merged_df = pd.merge(
        incident_krt_df,
        demo_df,
        on='ukrdcid',
        how='inner'
    ).drop_duplicates()

    
    merged_df = merged_df[~merged_df.age.isna()]
    merged_df["age"] = merged_df["age"].astype(float)


    print(f"Gender distribution:\n{merged_df['gender'].value_counts()}")
    print(f"Average age at KRT start: {merged_df['age'].mean():.1f} years")
    
    # create age and gender distribution
    fig1 = px.histogram(
        merged_df, 
        x='age',
        color='gender',
        title=f'Age Distribution of survivint Incident KRT Patients in {FACILITY}',
        labels={'age': 'Age at end of window', 'count': 'Number of Patients'},
        nbins=20
    )
    fig1.write_html(os.path.join(OUTPUT_DIR, "age_distribution.html"))