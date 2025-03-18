import streamlit as st
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator
import plotly.express as px
from datetime import datetime

start_date = st.session_state["start_date"]
start_datetime = datetime(year=start_date.year, month=start_date.month, day=start_date.day)
calculator = DemographicStatsCalculator(
    st.session_state["ukrdc_session"], 
    facility=st.session_state["facility"], 
    date = start_datetime
)

output = calculator.extract_stats()
age_distribution = px.bar(
    x=output.age.data.x,
    y=output.age.data.y,
    title=output.age.metadata.title,
    labels={
        "x": output.age.metadata.axis_titles.x,
        "y": output.age.metadata.axis_titles.y,
    },
)

gender_dist = px.pie(
    values=output.gender.data.y,
    names=output.gender.data.x,
    title=output.gender.metadata.title,
    hole=0.3,
)

ethnicity_dist = px.pie(
    values=output.ethnic_group.data.y,
    names=output.ethnic_group.data.x,
    title=output.ethnic_group.metadata.title,
    hole=0.3,
)

st.markdown(
    f"""
    # Facility Demographics Page
    Calculated for facility {st.session_state['facility']} 
    on {st.session_state["end_date"]}
    """
)

# age distribution
st.plotly_chart(age_distribution)

# gender distribution
st.plotly_chart(gender_dist)

# ethnicity distribution
st.plotly_chart(ethnicity_dist)