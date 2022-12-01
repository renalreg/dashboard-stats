"""
Module to contain the long descriptions for the pydantic output
"""

from textwrap import dedent


dialysis_descriptions = {
    "ALL_PATIENTS_HOME_THERAPIES": dedent(
        """
        # All Patients Home Therapies

        For a specified unit and time window, _All Patients Home Therapies_ contain the following numbers:
        * Number of patients on Haemodialysis. This is defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments.
        * Number of patients on Peritoneal Dialysis. Defined as the number of patients registered for CAPD or APD treatments.
        * Number of patients on home therapies. Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of patients on In centre therapies. Total number of patients registered for Haemodialysis in-centre

        The cohort is created from all the patients which are admitted for treatments: haemodialysis, haemofiltration, haemodiafiltration, ultrafiltration at the specified unit.These numbers are calculated from the Patient and Treatment records in the UKRDC. The patients are selected using the admission reason and the unit. Patients are further split into home and in-centre therapy groups (all patients on PD are included in the home therapies group).
        """
    ),
    "INCIDENT_HOME_THERAPIES": dedent(
        """
        # Incident Patients Home Therapies

        For a specified unit and time window, _Incident Patients Home Therapies_ contain the following numbers:
        * Number of incident patients on Haemodialysis. Defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments.
        * Number of incident patients on Peritoneal Dialysis. Defined as the number of patients registered for CAPD or APD treatments.
        * Number of incident patients on home therapies.Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of incident patients on In centre therapies.Total number of patients registered for Haemodialysis in-centre

        Incidence is defined as patients which start treatment without any dialysis or transplant treatments prior to the begining of the time window.
        """
    ),
    "PREVELENT_HOME_THERAPIES": dedent(
        """
        # Prevalent Patients Home Therapies

        For a specified unit and time window, _Prevalent Patients Home Therapies_ contain the following calculated numbers:
        * Number of prevalent patients on Haemodialysis. Defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments.
        * Number of prevalent patients on Peritoneal Dialysis. Defined as the number of patients registered for CAPD or APD treatments.
        * Number of prevalent patients on home therapies. Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of prevalent patients on In centre therapies. Total number of patients registered for Haemodialysis in-centre.

        Prevalence is defined as patients whose treatment spans the end of the time window.
    """
    ),
    "INCENTRE_DIALYSIS_FREQ": dedent(
        """
        # In-Centre Dialysis Frequency

        For a specific unit and time window _In-Centre Dialysis Frequency_ contains a histogram of the dialysis frequency of dialysis per person. For each member of the cohort frequency of dialysis is calculated by counting the number of dialysis sessions contained in the UKRDC and dividing by the difference in time between the first and last session. With a maximum value of 7 and a minimum value of 0 the data is binned into 15 bins. This leads to decimal values, which reflects that this is a frequency calculated over an arbitary time period.
        """
    ),
    "INCIDENT_INITIAL_ACCESS": dedent(
        """
        # Incident Intial Access

        This calculates the type of vascular access recorded in the UKRDC for the first dialysis session of incident patients. Incidence is defined as patients which start treatment without any dialysis or transplant treatments prior to the begining of the time window.
        """
    ),
}


demographic_descriptions = {
    "GENDER_DESCRIPTION": dedent(
        """
        # Patient Gender

        Translated gender identity codes recorded for each living patient registered with the renal unit over all time.
        """
    ),
    "ETHNIC_GROUP_DESCRIPTION": dedent(
        """
        # Patient Ethnicity

        Translated ethnicity group code recorded for each living patient registered with the renal unit over all time.
        The five ethnicity groupings used to map ethnicity codes onto the displayed ethnicity values are the same as those used in the Renal Registry Annual Report.
        """
    ),
    "AGE_DESCRIPTION": dedent(
        """
        # Patient Age

        The age, calcualated from date of birth, recorded for each living patient registered with the renal unit over all time.
        """
    ),
}
