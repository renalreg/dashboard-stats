from ukrdc_sqla.ukrdc import Patient, Treatment
from sqlalchemy import select
import dashboard_stats.models as oc

import pandas as pd
import datetime as dt


class Demog:
    """Calculates the demographics information based on the personal infomation listed in the patient table"""

    def __init__(self, session, facility, date=dt.datetime.today()):
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
        """
        Grab info on current patients by running select on Patient table for patient
        TODO:
            - Test if using pandas read_sql is slowing the code down
            - Security implications. Should patient cohort be a private variable?
            - Introduce pydantic to the fray
            - map to more meaningful labels
            - option of passing some sort of config which contains a list charts and types of chart to calculate?
            - validation method to pydantic class...for example that the sum of numbers should equal the total population
        """

        # select all patients with modalities that haven't finished
        patient_query = (
            select(Patient)
            .join(Treatment, Treatment.pid == Patient.pid)
            .filter(
                Treatment.health_care_facility_code == self.facility,
                (Treatment.from_time < self.date)
                & ((Treatment.to_time == None) | (Treatment.to_time >= self.date)),
                (Patient.death_time >= self.date) | (Patient.death_time == None),
            )
        )

        self.patient_cohort = pd.read_sql(patient_query, self.session.bind)

        # Crunch the numbers and make dataframes to produce "histograms" to display idividual bits of data
        pop_size = len(self.patient_cohort[["pid"]].drop_duplicates())

        make_hist = (
            lambda group: self.patient_cohort[["pid", group]]
            .drop_duplicates()
            .groupby([group])
            .count()
        )

        gender = make_hist("gender")
        birth_country = make_hist("countryofbirth")
        primary_language = make_hist("primarylanguagecode")
        ethnic_group_code = make_hist("ethnicgroupcode")
        occupation = make_hist("occupationcode")

        # Build output object

        self.patient_demog = oc.BarList(
            pop=pop_size,
            bars=[
                oc.Bar(
                    data=oc.Data(
                        labels=[item for item in gender.index],
                        values=[item[0] for item in gender.values],
                    ),
                    layout=oc.Layout(title="Gender"),
                ),
                oc.Bar(
                    data=oc.Data(
                        labels=[item for item in birth_country.index],
                        values=[item[0] for item in birth_country.values],
                    ),
                    layout=oc.Layout(title="Birth Country"),
                ),
                oc.Bar(
                    data=oc.Data(
                        labels=[item for item in primary_language.index],
                        values=[item[0] for item in primary_language.values],
                    ),
                    layout=oc.Layout(title="Primary Language"),
                ),
                oc.Bar(
                    data=oc.Data(
                        labels=[item for item in ethnic_group_code.index],
                        values=[item[0] for item in ethnic_group_code.values],
                    ),
                    layout=oc.Layout(title="Ethnic Group"),
                ),
                oc.Bar(
                    data=oc.Data(
                        labels=[item for item in occupation.index],
                        values=[item[0] for item in occupation.values],
                    ),
                    layout=oc.Layout(title="Occupation"),
                ),
            ],
        )

        return self.patient_demog
