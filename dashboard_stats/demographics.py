from ukrdc_sqla.ukrdc import Code, Patient, Treatment
from sqlalchemy.orm import aliased
from sqlalchemy import select
import dashboard_stats.utils as ut 
import pandas as pd
import datetime as dt

from pydantic import BaseModel 

# pydantic class for returning histograms 
class hist_item(BaseModel):
    label : str 
    count : int

class hist(BaseModel):
    label : str 
    hist_data : list    

class hists(BaseModel):
   hist_list : list


class Demog:
    """Calculates the demographics information based on the personal infomation listed in the patient table"""

    def __init__(self, session, facility, date = dt.datetime.today()):
        """Initialises the Demog class

        Args:
            session (SQLAlchemy session): Connection to database to calculate statistic from.
            facility (str): Facility to calculate the 
            date (datetime, optional): Date to calculate at. Defaults to today.
        """

        self.session = session 
        self.facility = facility
        self.date = date
        


    def patient_info(self):   
        '''
        Grab info on current patients by running select on Patient table for patient
        TODO:
            - Test if using pandas read_sql is slowing the code down
            - Security implications. Should patient cohort be a private variable?
            - Introduce pydantic to the fray 
            - map to more meaningful labels
            - option of passing some sort of config which contains a list of histograms to calculate? 
            - validation method to pydantic class...for example that the sum of numbers should equal the total population
        '''

        # select all patients with modalities that haven't finished
        patient_query = select(
            Patient
        ).join(
            Treatment, Treatment.pid == Patient.pid
        ).filter(
            Treatment.health_care_facility_code == self.facility,
            (Treatment.from_time < self.date) & ((Treatment.to_time == None) | (Treatment.to_time >= self.date)),
            (Patient.death_time >= self.date) | (Patient.death_time == None)
        )
        
        self.patient_cohort = pd.read_sql(patient_query, self.session.bind)        
        

        # Crunch the numbers and make dataframes to produce "histograms" to display idividual bits of data
        pop_size =  len(self.patient_cohort[["pid"]].drop_duplicates())
        
        make_hist = lambda group : self.patient_cohort[["pid", group]].drop_duplicates().groupby([group]).count()
 
        gender = make_hist("gender")
        birth_country = make_hist("countryofbirth")
        primary_language = make_hist("primarylanguagecode")
        ethnic_group_code = make_hist("ethnicgroupcode")
        occupation = make_hist("occupationcode")


        # build pydantic object
        self.patient_demog = hists(
            hist_list = [
                hist_item(label = 'Population Size', count = pop_size),
                hist(label = 'Gender', hist_data = [hist_item(label = label, count = count[0]) for label, count in zip(gender.index, gender.values)]),
                hist(label = 'Birth Country', hist_data = [hist_item(label = label, count = count[0]) for label, count in zip(birth_country.index, birth_country.values)]),
                hist(label = 'Primary Language', hist_data = [hist_item(label = label, count = count[0]) for label, count in zip(primary_language.index, primary_language.values)]),
                hist(label = 'Ethnic Group', hist_data = [hist_item(label = label, count = count[0]) for label, count in zip(ethnic_group_code.index, ethnic_group_code.values)]),
                hist(label = 'Occupation', hist_data = [hist_item(label = label, count = count[0]) for label, count in zip(occupation.index, occupation.values)])
            ]
        ) 


        return self.patient_demog