from ukrdc_sqla.ukrdc import Code, Patient
from sqlalchemy.orm import aliased
import pandas as pd


class Demog:
    """Calculates the demographics information based on the personal infomation listed in the patient table"""

    def __init__(self, session, unit):
        """initalises class

        Args:
            session (UKRDC SqlAlchemy session):
            unit (str): unit to calculate the statistics for.
        """

        self.session = session
        self.unit = unit

    def patient_info(self):
        # print('')

        codes_occ = aliased(Code)
        codes_ethnicity = aliased(Code)
        codes_language = aliased(Code)
        codes_occ = aliased(Code)

        self.patient_cohort = pd.DataFrame(
            self.sesh.query(
                Patient.pid,
                Patient.birth_time,
                Patient.gender,
                Patient.country_of_birth,
                Patient.ethnic_group_code,
                Patient.ethnic_group_description,
                Patient.primary_language,
                Patient.primary_language_codestd,
                Patient.primary_language_description,
                Patient.occupation_code,
                Patient.occupation_description,
                Patient.occupation_codestd,
            )
            .join(Treatment, Treatment.pid == Patient.pid)
            .filter(Treatment.health_care_facility_code == self.facility)
            .all()
        )

        self.patient_demog = {
            "population size": len(self.patient_cohort[["pid"]].drop_duplicates()),
            "gender": self.patient_cohort[["pid", "gender"]]
            .drop_duplicates()
            .groupby(["gender"])
            .count()
            .to_dict()["pid"],
            "birth country": self.patient_cohort[["pid", "country_of_birth"]]
            .drop_duplicates()
            .groupby(["country_of_birth"])
            .count()
            .to_dict()["pid"],
            "primary language": self.patient_cohort[["pid", "primary_language"]]
            .drop_duplicates()
            .groupby(["primary_language"])
            .count()
            .to_dict()["pid"],
            "ethnic_group_code": self.patient_cohort[["pid", "ethnic_group_code"]]
            .drop_duplicates()
            .groupby(["ethnic_group_code"])
            .count()
            .to_dict()["pid"],
            "occupation code": self.patient_cohort[["pid", "occupation_code"]]
            .drop_duplicates()
            .groupby(["occupation_code"])
            .count()
            .to_dict()["pid"],
        }
