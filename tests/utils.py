from sqlalchemy.orm import Session
from ukrdc_sqla.ukrdc import Address, Name, Patient, PatientNumber, PatientRecord
from mimesis import Generic
from mimesis.locales import Locale

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


def create_demo_patient(
    id_: int,
    seed: str,
    sending_facility: str,
    sending_extract: str,
    ukrdc3: Session,
):
    """Create a demo patient with the given ID"""
    generic = Generic(Locale.EN_GB, seed=seed)

    pid = f"{id_:10d}"

    record = PatientRecord(
        pid=pid,
        sendingfacility=sending_facility,
        sendingextract=sending_extract,
        localpatientid=f"{generic.numeric.integer_number(0):10d}",
        ukrdcid=f"{generic.numeric.integer_number(0):10d}",
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
