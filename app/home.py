import streamlit as st
from rr_connection_manager import PostgresConnection
from datetime import datetime, timedelta, date


# Set default values if not already in session_state
if "facility" not in st.session_state:
    st.session_state["facility"] = "RJZ"

if "start_date" not in st.session_state:
    st.session_state["start_date"] = date.today() 

if "num_days" not in st.session_state:
    st.session_state["num_days"] = 90

if "ukrdc_session" not in st.session_state:
    conn = PostgresConnection(app = "ukrdc_staging", tunnel = True, via_app = True)
    conn.connection_check()
    session = conn.session()
    st.session_state["ukrdc_session"] = session


# Function to update facility in session_state
def update_facility():
    st.session_state["facility"] = st.session_state["selected_facility"]

def update_start_date():
    st.session_state["start_date"] = st.session_state["selected_start_date"]

def update_end_date():
    st.session_state["end_date"] = st.session_state["start_date"] + timedelta(days=st.session_state["num_days"])


# List of facilities
facilities = ["RFBAK", "RJZ", "RNJ00", "RJE01"]


# Facility dropdown initialized with value from session_state
selected_facility = st.selectbox(
    "Pick a facility:",
    facilities,
    index=facilities.index(st.session_state["facility"]),  # Initialize the dropdown with the session state value
    key="selected_facility",  # This writes the selected value to session_state["selected_facility"]
    on_change=update_facility  # Update session_state when the facility changes
)


# Display selected facility
st.write(f"Selected Facility: {st.session_state['facility']}")


# Start date selector
selected_start_date = st.date_input(
    "Select start date:",
    value=st.session_state["start_date"],  # Use start date from session_state
    key = "selected_start_date",
    min_value=datetime(2000, 1, 1),
    max_value=datetime.today()
)



# Update the start date in session_state
st.session_state["start_date"] = selected_start_date

# Display the start date
st.write(f"Start Date: {st.session_state['start_date']}")

# Slider for number of months
months_slider = st.slider(
    "Select number of days:",
    min_value=7,
    max_value=366,
    value=st.session_state["num_days"],  
    key="num_days",
    on_change= update_end_date
)