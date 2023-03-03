"""
Module to contain the long descriptions for the pydantic output
"""
from textwrap import dedent

dialysis_descriptions = {
    "ALL_PATIENTS_HOME_THERAPIES": dedent(
        """
        # All Patients Undergoing Kidney Replacement Therapy

        ## Overview
        This pie chart illustrates the proportion of patients who received kidney replacement therapy within the time period. The chart is broken down by the type of treatment, including HD In-center, HD Home, HD Unknown/Incomplete, PD, and Tx. Optionally the chart can be filtered by satellite unit. 

        ## Treatment Definitions
        - HD: Haemodialysis patients (with a modality defined as HD by the UKRDC). This includes patients registered for haemodialysis, haemofiltration, haemodiafiltration, or ultrafiltration. 
        - PD: Peritoneal dialysis (with a modality defined as PD by the UKRDC).This includes patients registered for CAPD or APD treatments.
        - TX: Transplant patients (with a modality defined as TX), including both living and cadaver donors.
        - In-centre: HD patients with qbl05 field of the Treatment table as HOSP or SATL.   
        - Home: HD patients with qbl05 field of the Treatment table as HOME. 
        - Unknown/Incomplete: HD patients with incomplete qbl05 field or anything other than HOME, HOSP, or SATL

        ## Methodology 
        - Any patients with a time of death before the beginning of the time window were excluded from the cohort, as were any patients whose treatments started before and ended after it.
        - Patient's therapy types was selected using the admission reason and the unit, and were further split into home and in-center therapy groups (with all patients on PD included in the home therapies group).
        - The numbers were calculated from aggregating patients within the five groups: HD Home, HD In-centre, HD Unknown/Incomplete, PD and TX.
        - No deduplication is applied to the treatment records so patients with multiple treatments will be double counted
                
        ## UKRDC Entities Used
        The chart was produced by joining the following UKRDC entities according to their foreign key relationships:
        - [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): ukrdcid, sendingextract
        - [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): deathtime
        - [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): qbl05, hdp04, fromtime, totime, dischargereasoncode, healthcarefacilitycode
        - [ModalityCodes](https://renalregistry.atlassian.net/l/cp/Ac1YeFfH): registry_code_type
        """
    ),
    "INCIDENT_HOME_THERAPIES": dedent(
        """
        # Incident Patients Undergoing Kidney Replacement Therapy

        ## Overview
        This pie chart illustrates the modality of incident (new) kidney replacement therapy patients within the time window. The chart is broken down by type of treatment, including HD In-center, HD Home, HD Unknown/Incomplete, and PD. Optionally the chart can be filtered by satellite unit.

        ## Treatment Definitions
        - HD: Haemodialysis patients (with a modality defined as HD by the UKRDC). This includes patients registered for haemodialysis, haemofiltration, haemodiafiltration, or ultrafiltration. 
        - PD: Peritoneal dialysis (with a modality defined as PD by the UKRDC).This includes patients registered for CAPD or APD treatments.
        - TX: Transplant patients (with a modality defined as TX), including both living and cadaver donors.
        - In-centre: HD patients with qbl05 field of the Treatment table as HOSP or SATL.   
        - Home: HD patients with qbl05 field of the Treatment table as HOME. 
        - Unknown/Incomplete: HD patients with incomplete qbl05 field or anything other than HOME, HOSP, or SATL

        ## Study Methods
        - The cohort was created from all patients admitted for kidney replacement therapy (as defined by the modality code mappings) at the specified unit or satellite unit.
        - Any patients with a time of death before the beginning of the time window were excluded from the cohort, as were any patients whose treatments started before and ended after it.
        - Any patient with a transplant or dialysis treatment prior to the beginning of the time window was excluded.
        - The numbers were calculated from the Patient and Treatment records in the UKRDC.
        - Patient's therapy types was selected using the admission reason and the unit, and were further split into home and in-center therapy groups (with all patients on PD included in the home therapies group).
        - Where patients have multiple treatment records within the time window they are deduplicated using the treatment modality with the earliest starting date.
        
        ## UKRDC Entities Used
        The chart was produced by joining the following UKRDC entities according to their foreign key relationships:
        - [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): ukrdcid, sendingextract
        - [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): deathtime
        - [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): qbl05, hdp04, fromtime, totime, dischargereasoncode, healthcarefacilitycode
        - [ModalityCodes](https://renalregistry.atlassian.net/l/cp/Ac1YeFfH): registry_code_type
        """
    ),
    "PREVALENT_HOME_THERAPIES": dedent(
        """
        # Prevalent Patients Undergoing Kidney Replacement Therapy

        ## Overview
        This pie chart illustrates the proportion of prevalent (to the end of the time window) patients who received kidney replacement therapy at a specified unit during a three-month period prior to the current date. The chart is broken down by type of treatment, including HD In-center, HD Home, HD Unknown/Incomplete, and PD. Optionally the chart can be filtered by satellite unit.

        ## Treatment Definitions
        - HD: Haemodialysis patients (with a modality defined as HD by the UKRDC). This includes patients registered for haemodialysis, haemofiltration, haemodiafiltration, or ultrafiltration. 
        - PD: Peritoneal dialysis (with a modality defined as PD by the UKRDC).This includes patients registered for CAPD or APD treatments.
        - TX: Transplant patients (with a modality defined as TX), including both living and cadaver donors.
        - In-centre: HD patients with qbl05 field of the Treatment table as HOSP or SATL.   
        - Home: HD patients with qbl05 field of the Treatment table as HOME. 
        - Unknown/Incomplete: HD patients with incomplete qbl05 field or anything other than HOME, HOSP, or SATL

        ## Study Methods
        - The cohort was created from all patients admitted for HD or PD (as defined by the modality code mappings) at the specified unit or satellite unit.
        - Any patients with a time of death before the beginning of the time window were excluded from the cohort, as were any patients whose treatments started before and ended after it.
        - Any patient with a treatment to time or date of death before todays date are excluded
        - Any patient with a transplant or dialysis treatment prior to the beginning of the time window was excluded.
        - The numbers were calculated from the Patient and Treatment records in the UKRDC.
        - Patient's therapy types was selected using the admission reason and the unit, and were further split into home and in-center therapy groups (with all patients on PD included in the home therapies group).
        - Where there are multiple treatment modalities which overlap with the end of the time window the one with the most recent end date is selected. 

        ## UKRDC Entities Used
        The chart was produced by joining the following UKRDC entities according to their foreign key relationships:
        - [PatientRecord](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450149/PatientRecord): ukrdcid, sendingextract
        - [Patient](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450145/Patient): deathtime
        - [Treatment](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2006450155/Treatment+Encounter): qbl05, hdp04, fromtime, totime, dischargereasoncode, healthcarefacilitycode
        - [ModalityCodes](https://renalregistry.atlassian.net/l/cp/Ac1YeFfH): registry_code_type
    """
    ),
    "INCENTRE_DIALYSIS_FREQ": dedent(
        """
        # In-Centre Dialysis Frequency

        ## Overview
        This histogram represents the mean number of dialysis sessions per week for all dialysis patients in a three month period at a sendingfacility or one of its satellites. Optionally the chart can be filtered by satellite unit. 

        ## Methodology
        - Dialysis sessions are counted for patients in the 'All Patients Undergoing Kidney Replacement Therapy' cohort. This is done by grouping on the procedure type code. 
        - Patients with less than two sessions are rejected. 
        - The per week frequency is calculated for each person by dividing the count by the time difference between their first and last dialysis session within the three month period.
        - Patients are aggregated into bins of with boundaries (0.5, 1.5, 2.5, 3.5, 7.0). This are labelled 1,2,3 and >3 sessions per week.  

        ## UKRDC Entities Used
        The dialysis sessions table is queried by grouping by ukrdcid with the following aggregate functions used:
        - https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2005565449/Dialysis+Session+Procedure: MIN(fromtime), MAX(totime), COUNT(sessiontype).
        """
    ),
    "INCIDENT_INITIAL_ACCESS": dedent(
        """
        # Incident Initial Access
        ## Overview
        This pie chart shows the vascular access recorded on the first dialysis session of each incident patient. Optionally the chart can be filtered by satellite unit.

        ## Methodology
        - This cohort is identical to that used for incident patients treatment breakdown.
        - The first session is selected by ranking the dialysis sessions in time.
        - If the type of vascular access has been recorded it is counted accordingly otherwise it is counted as Unknown/Incomplete.
       
       ## UKRDC Entities Used
        - [Dialysis Session](https://renalregistry.atlassian.net/wiki/spaces/UD/pages/2005565449/Dialysis+Session+Procedure) qhd20 for first dialysis session. 
        """
    ),
}
demographic_descriptions = {
    "GENDER_DESCRIPTION": dedent(
        """
        # Patient Gender
        Gender identity recorded for each living patient registered with the renal unit.
        
        # Methodology
        - Patient records are matched to NHS stated gender using patient demographic information 
        - Patients are optionally checked against NHS tracing to check for date of death
        - All living patients with patient records sent by a particular sending facility are aggregated based on gender


        ## UKRDC Entities Used
        - [PatientRecord](https://renalregistry.atlassian.net/l/cp/KCZ6A2bX)
        - [Patient](https://renalregistry.atlassian.net/l/cp/0MXHtpTU)
        
        """
    ),
    "ETHNIC_GROUP_DESCRIPTION": dedent(
        """
        # Patient Ethnicity

        ## Overview 
        Ethnicity group code recorded for each living patient registered with the renal unit over all time.
        The five ethnicity groupings used to map ethnicity codes onto the displayed ethnicity values are the same as those used in the Renal Registry Annual Report.
        
        ## Methodology
        - Patient records are matched to ethnicity using patient demographic information 
        - Patients are optionally checked against NHS tracing to check for date of death
        - All living patients with patient records sent by a particular sending facility are aggregated based on ethnicity

        ## UKRDC Entities Used
        - [PatientRecord](https://renalregistry.atlassian.net/l/cp/KCZ6A2bX)
        - [Patient](https://renalregistry.atlassian.net/l/cp/0MXHtpTU)
        
        """
    ),
    "AGE_DESCRIPTION": dedent(
        """
        # Patient Age
        The age, calculated from date of birth, recorded for each living patient registered with the renal unit.
        
        # Methodology
        - Patient records are matched to date of birth using patient demographic information 
        - Age is calculated from date of birth 
        - Patients are optionally checked against NHS tracing to check for date of death
        - All living patients with patient records sent by a particular sending facility are aggregated based on age
        
        ## UKRDC Entities Used
        - [PatientRecord](https://renalregistry.atlassian.net/l/cp/KCZ6A2bX)
        - [Patient](https://renalregistry.atlassian.net/l/cp/0MXHtpTU)
        """
    ),
}
