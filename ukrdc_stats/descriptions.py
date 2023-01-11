"""
Module to contain the long descriptions for the pydantic output
"""
from textwrap import dedent

dialysis_descriptions = {
    "ALL_PATIENTS_HOME_THERAPIES": dedent(
        """
        # All Patients Treatment Breakdown

        ## Overview
        This pie chart illustrates the proportion of patients who received renal replacement therapy at a specified unit during a three-month period prior to the current date. The chart is broken down by type of treatment, including HD In-center, HD Home, HD Unknown/Incomplete, and PD.

        ## Treatment Definitions
        - HD In-center: patients registered for haemodialysis, haemofiltration, haemodiafiltration, or ultrafiltration treatments within the unit or satellite unit.
        - HD Home: patients registered for any of the above treatments at home.
        - HD Unknown/Incomplete: patients for whom it is not recorded whether treatment was received at home or in-center.
        - PD: patients registered for CAPD or APD treatments.

        ## Study Methods
        - The cohort was created from all patients admitted for HD or PD (as defined by the modality code mappings) at the specified unit or satellite unit.
        - Any patients with a time of death before the beginning of the time window were excluded from the cohort, as were any patients whose treatments started before and ended after it.
        - The numbers were calculated from the Patient and Treatment records in the UKRDC.
        - Patient's therapy types was selected using the admission reason and the unit, and were further split into home and in-center therapy groups (with all patients on PD included in the home therapies group).
        - [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): UKRDCID, PID fields were used to uniquely count patients.
        - [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): death time was used to exclude patients who were no longer alive at the beginning of the time window.
        - [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): admit_reason_code was used to identify dialysis patients.
        - [ModalityCodes](https://renalregistry.atlassian.net/l/cp/Ac1YeFfH): a comprehensive list of code mappings to match the admit_reason_code to HD and PD.
        """
    ),
    "INCIDENT_HOME_THERAPIES": dedent(
        """
        # Incident Patients Treatment Breakdown

        ## Overview
        This pie chart illustrates the proportion of incident (new) patients who received renal replacement therapy at a specified unit during a three-month period prior to the current date. The chart is broken down by type of treatment, including HD In-center, HD Home, HD Unknown/Incomplete, and PD.

        ## Treatment Definitions
        - HD In-center: patients registered for haemodialysis, haemofiltration, haemodiafiltration, or ultrafiltration treatments within the unit or satellite unit.
        - HD Home: patients registered for any of the above treatments at home.
        - HD Unknown/Incomplete: patients for whom it is not recorded whether treatment was received at home or in-center.
        - PD: patients registered for CAPD or APD treatments.

        ## Study Methods
        - The cohort was created from all patients admitted for HD or PD (as defined by the modality code mappings) at the specified unit or satellite unit.
        - Any patients with a time of death before the beginning of the time window were excluded from the cohort, as were any patients whose treatments started before and ended after it.
        - Any patient with a transplant or dialysis treatment prior to the beginning of the time window was excluded.
        - The numbers were calculated from the Patient and Treatment records in the UKRDC.
        - Patient's therapy types was selected using the admission reason and the unit, and were further split into home and in-center therapy groups (with all patients on PD included in the home therapies group).
        - [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): UKRDCID, PID fields were used to uniquely count patients.
        - [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): death time was used to exclude patients who were no longer alive at the beginning of the time window.
        - [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): admit_reason_code was used to identify dialysis patients.
        - [ModalityCodes](https://renalregistry.atlassian.net/l/cp/Ac1YeFfH): a comprehensive list of code mappings to match the admit_reason_code to HD and PD.
        """
    ),
    "PREVALENT_HOME_THERAPIES": dedent(
        """
        # Prevalent Patients Treatment Breakdown

        ## Overview
        This pie chart illustrates the proportion of prevalent (to today's date) patients who received renal replacement therapy at a specified unit during a three-month period prior to the current date. The chart is broken down by type of treatment, including HD In-center, HD Home, HD Unknown/Incomplete, and PD.

        ## Treatment Definitions
        - HD In-center: patients registered for haemodialysis, haemofiltration, haemodiafiltration, or ultrafiltration treatments within the unit or satellite unit.
        - HD Home: patients registered for any of the above treatments at home.
        - HD Unknown/Incomplete: patients for whom it is not recorded whether treatment was received at home or in-center.
        - PD: patients registered for CAPD or APD treatments.

        ## Study Methods
        - The cohort was created from all patients admitted for HD or PD (as defined by the modality code mappings) at the specified unit or satellite unit.
        - Any patients with a time of death before the beginning of the time window were excluded from the cohort, as were any patients whose treatments started before and ended after it.
        - Any patient with a treatment to time or date of death before todays date are excluded
        - Any patient with a transplant or dialysis treatment prior to the beginning of the time window was excluded.
        - The numbers were calculated from the Patient and Treatment records in the UKRDC.
        - Patient's therapy types was selected using the admission reason and the unit, and were further split into home and in-center therapy groups (with all patients on PD included in the home therapies group).
        - [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): UKRDCID, PID fields were used to uniquely count patients.
        - [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): death time was used to exclude patients who were no longer alive at the beginning of the time window.
        - [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): admit_reason_code was used to identify dialysis patients.
        - [ModalityCodes](https://renalregistry.atlassian.net/l/cp/Ac1YeFfH): a comprehensive list of code mappings to match the admit_reason_code to HD and PD.
    """
    ),
    "INCENTRE_DIALYSIS_FREQ": dedent(
        """
        # In-Centre Dialysis Frequency

        ## Interpretation
        Each bar in the histogram represents the average number of dialysis treatments per week for a specific unit and time window for a group of patients.

        ## Definition
        The In-Centre dialysis frequency histogram displays the frequency of dialysis treatments per person for patients registered for in-centre dialysis. The frequency is determined by counting the number of dialysis sessions for each patient and dividing that by the time difference between the first and last session. The data is then grouped into 7 bins with a minimum value of 0 and a maximum value of 7.

        ## Study Methods
        - This cohort used is identical to that of all patients treatment breakdown.
        - The data is stored in the patient record and dialysis session tables.
        - [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord)
        - [Dialysis Session](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2005565449/Dialysis+Session+Procedure) - The proceduretypecode, fromtime, and totime fields were used to count the number of sessions per person and calculate the frequency.

        """
    ),
    "INCIDENT_INITIAL_ACCESS": dedent(
        """
        # Incident Initial Access
        ## Interpretation
        Segment of pie chart records which proportion of incident patients have that type of vascular access recorded on their first session.
        ## Definition
        The type of vascular access recorded in the UKRDC for the first dialysis session of incident patients. Incidence is defined as patients which start treatment without any dialysis or transplant treatments prior to the beginning of the time window.
        ## Study Methods
        - This cohort is identical to that used for incident patients treatment breakdown
        - patients with less than 2 dialysis sessions were rejected
        - [Dialysis Session](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2005565449/Dialysis+Session+Procedure) qhd20 of the first recorded dialysis record
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
