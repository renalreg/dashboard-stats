import streamlit as st


st.markdown(
    f"""
    # Kidney Replacement Therapy
    Calculated for facility {st.session_state['facility']} 
    between {st.session_state["start_date"]} 
    and {st.session_state["end_date"]}
    """
)


