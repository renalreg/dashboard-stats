from textwrap import dedent

# this file contains the long desriptions of all the statistics returned by the api


dialysis_descriptions = {
    "ALL_PATIENTS_HOME_THERAPIES": dedent(
        """ 
        # All Patients Home Therapies 

        For a specified unit and time window All Patients Home Therapies contain the following numbers:  
        * Number of patients on Haemodialysis. This is defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments. 
        * Number of patients on Peritoneal Dialysis.Defined as the number of patients registered for CAPD or APD treatments.
        * Number of patients on home therapies. Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of patients on In centre therapies. Total number of patients registered for Haemodialysis in-centre

        These numbers are calculated from the Patient and Treatment records in the UKRDC. The patients are selected using the admission reason and the unit. The cohort is created from all the patients which are admitted for treatments: haemodialysis, haemofiltration, haemodiafiltration, ultrafiltration at the specified unit.

        For this patient cohort, the numbers of patients on Haemodialysis and Peritoneal dialysis is calculated. The patients are also split into home and incentre therapy groups with the intrinsic assumption that all patients on PD have home therapies.
        """
    ),
    "INCIDENT_HOME_THERAPIES": dedent(
        """
        # Incident Patients Home Therapies 
        For a specified unit and time window contains :  
        * Number of incident patients on Haemodialysis. Defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments.
        * Number of incident patients on Peritoneal Dialysis. Defined as the number of patients registered for CAPD or APD treatments.
        * Number of incident patients on home therapies.Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of incident patients on In centre therapies.
        
        Total number of patients registered for Haemodialysis in-centre

        Incidence in this instance is defined as the patients who begin treatment within the time window and have no other registered dialysis or transplant modalities. 
        """
    ),
    "PREVELENT_HOME_THERAPIES": dedent(
        """
        # Prevalent Patients Home Therapies 

        For a specified unit and time window contains:  
        * Number of prevalent patients on Haemodialysis. Defined as the number of patients registered for haemodialysis, haemofiltration, haemodiafiltration or ultrafiltration treatments.
        * Number of prevalent patients on Peritoneal Dialysis. Defined as the number of patients registered for CAPD or APD treatments.
        * Number of prevalent patients on home therapies. Total number of patients on Peritoneal Dialysis as defined above combined with the number of patients on heamodialysis on home therapies.
        * Number of prevalent patients on In centre therapies. Total number of patients registered for Haemodialysis in-centre. 

        Incidence in this instance is defined as the patients who begin treatment within the time window and have no other registered dialysis or transplant modalities. 
    """
    ),
    "INCENTRE_DIALYSIS_FREQ": dedent(
        """
        ipsum lopsum quantum 
        """
    ),
    "INCIDENT_INITIAL_ACCESS": dedent(
        """
        ipsum lopsum quantum 
        """
    ),
}


demographic_descriptions = {
    "GENDER_DESCRIPTION": dedent(
        """
        ipsum lopsum quantum 
        """
    ),
    "ETHNIC_GROUP_DESCRIPTION": dedent(
        """
        ipsum lopsum quantum 
        """
    ),
    "AGE_DESCRIPTION": dedent(
        """
        ipsum lopsum quantum 
        """
    ),
}
