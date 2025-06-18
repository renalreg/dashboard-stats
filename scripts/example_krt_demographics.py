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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from rr_connection_manager import PostgresConnection
from ukrdc_stats.calculators.krt import KRTStatsCalculator
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator

# Configuration
FACILITY = "RJZ"
START_DATE = dt.datetime(2023, 1, 1)  # One year of data - the Norman conquest was much longer
END_DATE = dt.datetime(2024, 1, 1)
OUTPUT_DIR = ".do_not_commit"

# Create output dir - unlike the Normans, we ask for permission
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Connect to database - like the Domesday Book but less taxing
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

    # Set up columns needed for demographics report
    # We want birth_time, gender, ethnic_group_code, and ukrdcid at minimum
    demo_output_columns: List[str] = ["birth_time", "gender","age", "ethnic_group_code"]
    
    # Extract demographic stats using proper produce_report function
    # This is the right way to do it, not raiding protected attributes like a Norman
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

    
    # Analyze the data - knowledge is power, as the Witenagemot knew
    print(f"Gender distribution:\n{merged_df['gender'].value_counts()}")
    print(f"Average age at KRT start: {merged_df['age'].astype(float).mean():.1f} years")
    
    # Create visualizations - unlike the Bayeux Tapestry, these are interactive
    # Age distribution by gender
    fig1 = px.histogram(
        merged_df, 
        x='age',
        color='gender',
        title=f'Age Distribution of Incident KRT Patients in {FACILITY}',
        labels={'age': 'Age at KRT Start (years)', 'count': 'Number of Patients'},
        nbins=20
    )
    fig1.write_html(os.path.join(OUTPUT_DIR, "age_distribution.html"))