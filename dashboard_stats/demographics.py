import datetime as dt

import pandas as pd
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import Patient, Treatment

from dashboard_stats.models import Bar, BarList, Data, Layout


class PatientDemographicStats:
    """Calculates the demographics information based on the personal infomation listed in the patient table"""

    def __init__(
        self,
        session: Session,
        facility: str,
        date: dt.datetime = dt.datetime.today(),
    ):
        """Initialises the PatientDemographicStats class and immediately runs the relevant query

        Args:
            session (SQLAlchemy session): Connection to database to calculate statistic from.
            facility (str): Facility to calculate the
            date (datetime, optional): Date to calculate at. Defaults to today.
        """

        self.session: Session = session
        self.facility: str = facility
        self.date: dt.datetime = date

        # Immediately run the patient cohort query, so it's ready for re-use
        self.patient_cohort: pd.DataFrame = self._extract_patient_cohort()

    def _extract_patient_cohort(self) -> pd.DataFrame:
        """
        Extracts the patient cohort from the database into a pandas dataframe
        """
        # select all patients with modalities that haven't finished
        patient_query = (
            self.session.query(Patient)
            .join(Treatment, Treatment.pid == Patient.pid)
            .filter(
                Treatment.health_care_facility_code == self.facility,
                (Treatment.from_time < self.date)
                & ((Treatment.to_time is None) | (Treatment.to_time >= self.date)),
                (Patient.death_time >= self.date) | (Patient.death_time is None),
            )
        )

        return pd.read_sql(patient_query, self.session.bind)

    def _make_patient_histogram(self, group: str) -> pd.DataFrame:
        return (
            self.patient_cohort[["pid", group]]
            .drop_duplicates()
            .groupby([group])
            .count()
        )

    def patient_info(self):
        """
        Extract demographic statistics from the patient cohort dataframe
        TODO:
            - Test if using pandas read_sql is slowing the code down
            - Security implications. Should patient cohort be a private variable?
            - Introduce pydantic to the fray
            - map to more meaningful labels
            - option of passing some sort of config which contains a list charts and types of chart to calculate?
            - validation method to pydantic class...for example that the sum of numbers should equal the total population
        """

        # Crunch the numbers and make dataframes to produce "histograms" to display idividual bits of data
        pop_size = len(self.patient_cohort[["pid"]].drop_duplicates())

        gender = self._make_patient_histogram("gender")
        birth_country = self._make_patient_histogram("countryofbirth")
        primary_language = self._make_patient_histogram("primarylanguagecode")
        ethnic_group_code = self._make_patient_histogram("ethnicgroupcode")
        occupation = self._make_patient_histogram("occupationcode")

        # Build output object

        return BarList(
            pop=pop_size,
            bars=[
                Bar(
                    data=Data(
                        labels=list(gender.index),
                        values=[item[0] for item in gender.values],
                    ),
                    layout=Layout(title="Gender"),
                ),
                Bar(
                    data=Data(
                        labels=list(birth_country.index),
                        values=[item[0] for item in birth_country.values],
                    ),
                    layout=Layout(title="Birth Country"),
                ),
                Bar(
                    data=Data(
                        labels=list(primary_language.index),
                        values=[item[0] for item in primary_language.values],
                    ),
                    layout=Layout(title="Primary Language"),
                ),
                Bar(
                    data=Data(
                        labels=list(ethnic_group_code.index),
                        values=[item[0] for item in ethnic_group_code.values],
                    ),
                    layout=Layout(title="Ethnic Group"),
                ),
                Bar(
                    data=Data(
                        labels=list(occupation.index),
                        values=[item[0] for item in occupation.values],
                    ),
                    layout=Layout(title="Occupation"),
                ),
            ],
        )
