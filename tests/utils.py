from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import (
    Address,
    Name,
    Patient,
    PatientNumber,
    PatientRecord,
    Treatment,
    DialysisSession
)
from mimesis import Generic
from mimesis.locales import Locale
from ukrdc_stats.dialysis import DialysisStatsCalculator

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

generic = Generic(Locale.EN_GB, seed="moo")


def create_demo_patient(
    id_: int, sending_facility: str, sending_extract: str, ukrdc3: Session
):
    """Create a demo patient with the given ID"""

    pid = f"test:{id_}"

    record = PatientRecord(
        pid=pid,
        sendingfacility=sending_facility,
        sendingextract=sending_extract,
        localpatientid=f"{generic.numeric.integer_number(0):10d}",
        # ukrdcid=f"{generic.numeric.integer_number(0):10d}",
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


def generate_treatment(
    id_: int,
    pid: str,
    health_care_facility: str,
    start_time: datetime,
    end_time: datetime,
    ukrdc3: Session,
):
    # generic = Generic(Locale.EN_GB, seed=seed)

    # randomly select treatment modality
    admit_reason_code = generic.choice(TREATMENT_MODALITY_CODES)

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
    id_:int, 
    pid:str, 
    session_period_start:datetime,
    session_period_end:datetime, 
    number_of_sessions: int,
    ukrdc3: Session,
):

    # generate equally spaced treatments in time window to keep things simple
    if number_of_sessions <= 1:
        timestep = (session_period_start - session_period_end)
    else: 
        timestep = (session_period_start - session_period_end) / (number_of_sessions -1)

    proceedure_time = session_period_start
    qhd20 = generic.choice(QHD20_CODES)
    for i in range(number_of_sessions):
        dialysis_session = DialysisSession(
            id = f"test:{id_}:{i}",
            procedure_type_code = "302497006",
            procedure_time = proceedure_time,
            qhd20 = qhd20 
        )
        ukrdc3.add(dialysis_session)

    return


