from datetime import datetime, timedelta
from typing import Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import (
    Address,
    Name,
    Patient,
    PatientNumber,
    PatientRecord,
    Treatment,
    DialysisSession,
)
from mimesis import Generic
from mimesis.locales import Locale

import warnings

ETHNICITY_GROUP_CODES = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "J",
    "K",
    "L",
    "M",
    "N",
    "P",
    "R",
    "S",
    "Z",
    "99",
]


TREATMENT_MODALITY_CODES = [
    "1",
    "2",
    "3",
    "5",
    "110",
    "11",
    "12",
    "20",
    "78",
    "29",
    "81",
    "82",
    "83",
    "88",
    "904",
    "903",
    "902",
    "900",
    "901",
]


DIALYSIS_MODALITY_CODES = ["1", "2", "3", "5", "11", "12"]


QHD20_CODES = ["TLN", "NLN", "AVF"]

QBL05_CODES = ["HOSP", "HOME"]


class FakeDataGenerator:
    def __init__(self, seed: str) -> None:
        self.seed = seed

        self.generics: Dict[str, Generic] = {}

    def reset_generics(self):
        self.generics: Dict[str, Generic] = {}

    def create_demo_patient(
        self, id_: int, sending_facility: str, sending_extract: str, ukrdc3: Session
    ):
        """Create a demo patient with the given ID"""
        generic = self.generics.setdefault(
            "demographics", Generic(Locale.EN_GB, seed=self.seed)
        )

        pid = f"test:{id_}"

        record = PatientRecord(
            pid=pid,
            sendingfacility=sending_facility,
            sendingextract=sending_extract,
            localpatientid=f"{generic.numeric.integer_number(0):10d}",
            ukrdcid=f"ukrdc_{pid}",
        )

        name = Name(
            id=id_,
            pid=pid,
            family=generic.person.last_name(),
            given=generic.person.first_name(),
            nameuse="L",
        )

        address = Address(
            id=id_,
            pid=pid,
            street=generic.address.address(),
            town=generic.address.city(),
            county=generic.address.state(),
            postcode=generic.address.postal_code(),
            country_description=generic.address.country(),
        )

        patient = Patient(
            pid=pid,
            birth_time=generic.datetime.date(start=1950, end=2010),
            gender=generic.person.gender(iso5218=True),
            ethnic_group_code=generic.choice(ETHNICITY_GROUP_CODES),
            country_of_birth=generic.address.country_code(),
        )
        patient_number = PatientNumber(
            id=id_,
            pid=pid,
            patientid=f"{generic.numeric.integer_number(0):10d}",
            organization="NHS",
            numbertype="NI",
        )

        ukrdc3.add(record)
        ukrdc3.add(name)
        ukrdc3.add(address)
        ukrdc3.add(patient)
        ukrdc3.add(patient_number)

        return pid

    def generate_dialysis_treatment(
        self,
        id_: int,
        pid: str,
        health_care_facility: str,
        start_time: datetime,
        end_time: datetime,
        ukrdc3: Session,
    ):
        generic = self.generics.setdefault(
            "dia_treatment", Generic(Locale.EN_GB, seed=self.seed)
        )

        # Forces admit reason code to a DIALYSIS_MODALITY_CODES code,
        # so every generated patient will be included in the dialysis stats extract

        # randomly select treatment modality
        admit_reason_code = generic.choice(DIALYSIS_MODALITY_CODES)

        qbl05 = None
        # select some other options based on modality
        if admit_reason_code in ["1", "2", "3", "5"]:
            qbl05 = generic.choice(QBL05_CODES)

        time_delta = timedelta(weeks=2)
        incident = generic.choice([True, False])
        prevalent = generic.choice([True, False])
        if incident:
            start_time = start_time + time_delta
        if prevalent:
            end_time = end_time + time_delta

        treatment = Treatment(
            id=f"test:{id_:10d}",
            pid=pid,
            health_care_facility_code=health_care_facility,
            admit_reason_code=admit_reason_code,
            from_time=start_time,
            to_time=end_time,
            qbl05=qbl05,
        )

        ukrdc3.add(treatment)

        return

    def generate_dialysis_session(
        self,
        id_: int,
        pid: str,
        session_period_start: datetime,
        session_period_end: datetime,
        number_of_sessions: int,
        ukrdc3: Session,
    ):
        generic = self.generics.setdefault(
            "dia_session", Generic(Locale.EN_GB, seed=self.seed)
        )

        # generate equally spaced treatments in time window to keep things simple
        if number_of_sessions <= 1:
            timestep = session_period_end - session_period_start
        else:
            timestep = (session_period_end - session_period_start) / (
                number_of_sessions - 1
            ) - timedelta(hours=2)

        procedure_time = session_period_start + timedelta(hours=1)
        qhd20 = generic.choice(QHD20_CODES)
        for i in range(number_of_sessions):
            dialysis_session = DialysisSession(
                id=f"test:{id_}:{i}",
                pid=pid,
                procedure_type_code="302497006",
                procedure_time=procedure_time,
                qhd20=qhd20,
            )
            ukrdc3.add(dialysis_session)
            procedure_time = procedure_time + timestep

        ukrdc3.commit()

        return


def check_required_metadata(stats_output: BaseModel):
    for k, stat in stats_output.dict().items():
        # Exclude top level metadata
        if k == "metadata":
            pass

        stat_metadata = stat.get("metadata", {})

        for field in ("title", "summary", "description"):
            if not stat_metadata.get(field):
                warnings.warn(f"Required metadata field {field} is empty for stat {k}")
