"""
Module to contain the long descriptions for the pydantic output
"""
from textwrap import dedent

dialysis_descriptions = {
    "ALL_PATIENTS_HOME_THERAPIES": dedent(
        """
        # All Patients Home Therapies
        ## Interpretation
        Flow of chart shows overlap between group on the left hand side and the group on the right hand side with the thickness representing the size of the overlap. For example a flow with a source in Haemodialysis ending in home therapies represents the number of patients on HHD.
        ## Definition
        For a specified unit and time window, _All Patients Home Therapies_ contain the following numbers:
        * Number of patients on Haemodialysis. This is defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments.
        * Number of patients on Peritoneal Dialysis. Defined as the number of patients registered for CAPD or APD treatments.
        * Number of patients on home therapies. Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of patients on In centre therapies. Total number of patients registered for Haemodialysis in-centre
        The cohort is created from all the patients which are admitted for treatments: haemodialysis, haemofiltration, haemodiafiltration, ultrafiltration at the specified unit.These numbers are calculated from the Patient and Treatment records in the UKRDC. The patients are selected using the admission reason and the unit. Patients are further split into home and in-centre therapy groups (all patients on PD are included in the home therapies group).
        ## UKRDC Elements Used
        The following tables and fields have been queried to generate these statistics:
        * [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): UKRDCID, PID fields are used uniquely count patients.
        * [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): death time used to exclude patients who are no longer alive at beginning of time window.
        * [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): admit_reason_code used to identify dialysis patients.
        """
    ),
    "INCIDENT_HOME_THERAPIES": dedent(
        """
        # Incident Patients Home Therapies
        ## Interpretation
        Flow of chart shows overlap between group on the left hand side and the group on the right hand side with the thickness representing the size of the overlap. For example a flow with a source in Haemodialysis ending in home therapies represents the number of patients on HHD.
        ## Definition
        For a specified unit and time window, _Incident Patients Home Therapies_ contain the following numbers:
        * Number of incident patients on Haemodialysis. Defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments.
        * Number of incident patients on Peritoneal Dialysis. Defined as the number of patients registered for CAPD or APD treatments.
        * Number of incident patients on home therapies.Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of incident patients on In centre therapies.Total number of patients registered for Haemodialysis in-centre
        Incidence is defined as patients which start treatment without any dialysis or transplant treatments prior to the begining of the time window.
        ## UKRDC Elements Used
        The following tables and fields have been queried to generate these statistics:
        * [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): UKRDCID, PID fields are used uniquely count patients.
        * [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): death time used to exclude patients who are no longer alive at beginning of time window.
        * [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): admit_reason_code used to identify dialysis patients, calculate incidence status and treatment start times.
        """
    ),
    "PREVALENT_HOME_THERAPIES": dedent(
        """
        # Prevalent Patients Home Therapies
        ## Interpretation
        Flow of chart shows overlap between group on the left hand side and the group on the right hand side with the thickness representing the size of the overlap. For example a flow with a source in Haemodialysis ending in home therapies represents the number of patients on HHD.
        ## Definition
        For a specified unit and time window, _Prevalent Patients Home Therapies_ contain the following calculated numbers:
        * Number of prevalent patients on Haemodialysis. Defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments.
        * Number of prevalent patients on Peritoneal Dialysis. Defined as the number of patients registered for CAPD or APD treatments.
        * Number of prevalent patients on home therapies. Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of prevalent patients on In centre therapies. Total number of patients registered for Haemodialysis in-centre.
        Prevalence is defined as patients whose treatment spans the end of the time window.
        ## UKRDC Elements Used
        The following tables and fields have been queried to generate these statistics:
        * [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): UKRDCID, PID fields are used uniquely count patients.
        * [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): death time used to exclude patients who are no longer alive at beginning of time window.
        * [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): admit_reason_code used to identify dialysis patients and treatment start times.
    """
    ),
    "INCENTRE_DIALYSIS_FREQ": dedent(
        """
        # In-Centre Dialysis Frequency
        ## Interpretation
        Each bar shows the number of patients which on average have the number of treatments per week in that window.
        ## Definition
        For a specific unit and time window, _In-Centre Dialysis Frequency_ contains a histogram of the dialysis frequency of dialysis per person. For dialysis patients registered for in-centre dialysis, frequency of dialysis is calculated by counting the number of dialysis sessions of a patient and dividing by the time difference of the first and last session. With a maximum value of 7 and a minimum value of 0 the data is binned into 15 bins.
        ## UKRDC Elements Used
        The following tables and fields have been queried to generate these statistics:
        * [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord)
        * [Dialysis Session](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2005565449/Dialysis+Session+Procedure) proceduretypecode, fromtime, totime are used to count the number of sessions per person and calculate frequency.
        """
    ),
    "INCIDENT_INITIAL_ACCESS": dedent(
        """
        # Incident Initial Access
        ## Interpretation
        Segment of pie chart records which proportion of incident patients have that type of vascular access recorded on their first session.
        ## Definition
        The type of vascular access recorded in the UKRDC for the first dialysis session of incident patients. Incidence is defined as patients which start treatment without any dialysis or transplant treatments prior to the beginning of the time window.
        ## UKRDC Elements Used
        The following tables and fields have been queried to generate these statistics:
        * [Dialysis Session](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2005565449/Dialysis+Session+Procedure) qhd20 of the first recorded dialysis record
        """
    ),
}
demographic_descriptions = {
    "GENDER_DESCRIPTION": dedent(
        """
        # Patient Gender
        Gender identity recorded for each living patient registered with the renal unit.
        """
    ),
    "ETHNIC_GROUP_DESCRIPTION": dedent(
        """
        # Patient Ethnicity
        Ethnicity group code recorded for each living patient registered with the renal unit over all time.
        The five ethnicity groupings used to map ethnicity codes onto the displayed ethnicity values are the same as those used in the Renal Registry Annual Report.
        """
    ),
    "AGE_DESCRIPTION": dedent(
        """
        # Patient Age
        The age, calculated from date of birth, recorded for each living patient registered with the renal unit.
        """
    ),
}
