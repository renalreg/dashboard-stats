import datetime as dt
from ukrdc_stats.cohorts.schema import krt_base_schema, demog_base_schema
from ukrdc_sqla.ukrdc import Treatment, Patient, PatientRecord, ModalityCodes, CodeMap
import pandera.pandas as pa
import pandas as pd
from ukrdc_stats.exceptions import EmptyCohortError
from sqlalchemy import select, exists, case, or_, func
from sqlalchemy.orm import Session, aliased


@pa.check_output(krt_base_schema)
def krt(
    session:Session,
    facility:str,
    end:dt.datetime,
    start:dt.datetime, 
    recovery_window:dt.timedelta = dt.timedelta(days=90)
) -> krt_base_schema:
        """Core query containing all of the data from the ukrdc database
        necessary to generate either an incident or prevalent krt cohort.

        Returns:
            krt_base_schema: Patient cohort dataframe
        """

        minimum_transplant_length = 7

        ChronicTreatment = aliased(Treatment)  # pylint: disable=C0103
        ChronicModality = aliased(ModalityCodes)  # pylint: disable=C0103
        HistoricTransplantTreatment = aliased(Treatment)  # pylint: disable=C0103
        TransplantModality = aliased(ModalityCodes)  # pylint: disable=C0103
        SubPatientRecord = aliased(PatientRecord)

        # Select ukrdcids of patients treated at facility
        ukrdc_sub = select(PatientRecord.ukrdcid).where(
            PatientRecord.sendingfacility == facility,
            PatientRecord.sendingextract == "UKRDC",
        )

        ckd_ranked = (
            select(
                ChronicTreatment.pid.label("pid"),
                ChronicTreatment.healthcarefacilitycode.label("ckd_centre"),
                func.row_number()
                .over(
                    partition_by=ChronicTreatment.pid,
                    order_by=ChronicTreatment.fromtime.desc(),
                )
                .label("rn"),
            )
            .select_from(ChronicTreatment)
            .join(
                ChronicModality,
                ChronicModality.registry_code == ChronicTreatment.admitreasoncode,
            )
            .where(
                ChronicTreatment.fromtime < end,
                ChronicModality.registry_code_type == "CK",
            )
        ).subquery("ckd_ranked")
        
        ckd_latest = (
            select(ckd_ranked.c.pid, ckd_ranked.c.ckd_centre)
            .where(ckd_ranked.c.rn == 1)
        ).subquery("ckd_latest")

        tx_check = exists().where(
            HistoricTransplantTreatment.pid == SubPatientRecord.pid,
            SubPatientRecord.ukrdcid == PatientRecord.ukrdcid,
            HistoricTransplantTreatment.fromtime
            < start,  # Before start of time window
            HistoricTransplantTreatment.totime - HistoricTransplantTreatment.fromtime
            > dt.timedelta(days=minimum_transplant_length),  # Successful transplant
            HistoricTransplantTreatment.admitreasoncode
            == TransplantModality.registry_code,
            TransplantModality.registry_code_type == "TX",
            SubPatientRecord.sendingextract == "UKRDC",
        )

        query = (
            select(
                PatientRecord.pid,
                PatientRecord.ukrdcid,
                PatientRecord.sendingfacility,
                Treatment.healthcarefacilitycode,
                Treatment.admitreasoncode,
                Treatment.admitreasoncodestd,
                Treatment.admissionsourcecode,
                Treatment.admissionsourcecodestd,
                Treatment.qbl05,
                Treatment.hdp04,
                Treatment.dischargereasoncode,
                Treatment.dischargereasoncodestd,
                Treatment.dischargelocationcode,
                Treatment.dischargelocationcodestd,
                ModalityCodes.registry_code_type,
                Patient.deathtime,
                Treatment.fromtime,
                Treatment.totime,
                ckd_latest.c.ckd_centre,
                # Correlated subquery for historical transplant check
                case(
                    (
                        tx_check,
                        True,
                    ),
                    else_=False,
                ).label("historic_tx"),
            )
            .select_from(PatientRecord)
            .join(Patient, Patient.pid == PatientRecord.pid)
            .join(Treatment, Treatment.pid == PatientRecord.pid)
            .join(
                ModalityCodes, ModalityCodes.registry_code == Treatment.admitreasoncode
            )
            .outerjoin(ckd_latest, ckd_latest.c.pid == PatientRecord.pid)
            .where(
                ModalityCodes.registry_code_type.in_(["HD", "PD", "TX"]),
                or_(
                    Treatment.totime > start - dt.timedelta(days=90),
                    Treatment.totime.is_(None),
                ),
                or_(
                    Patient.deathtime > start, Patient.deathtime.is_(None)
                ),
                PatientRecord.ukrdcid.in_(ukrdc_sub),
                PatientRecord.sendingextract == "UKRDC",
            )
        )

        # apply cutoff. Implicitly if calculating for date more recent than
        # cutoff we allow all fromtimes
        if dt.datetime.now() - end > recovery_window:
            query = query.where(Treatment.fromtime < end + recovery_window)
        
        data = session.execute(query).all()
        
        if not data:
            raise EmptyCohortError

        return pd.DataFrame(data)


@pa.check_output(demog_base_schema)
def facility_demographics(session:Session, facility_code:str)->krt_base_schema:
    query = (
        select(
            Patient.pid,
            Patient.birth_time,
            Patient.gender,
            Patient.ethnic_group_code,
            Patient.ethnic_group_code_std,
            Patient.ethnic_group_description,
        )
        .select_from(Patient)
        .join(PatientRecord, Patient.pid == PatientRecord.pid)
        .outerjoin(CodeMap, CodeMap.source_code == Patient.ethnic_group_code)
        .where(
            PatientRecord.facility == facility_code, 
            CodeMap.source_coding_standard == "NHS_DATA_DICTIONARY",
            CodeMap.destination_coding_standard == "URTS_ETHNIC_GROUPING"
        )
    )
    data = session.execute(query).all()
    
    if data:
        demographics =  pd.DataFrame(data)
    else:
        print(f"Warning no demographics extracted for facility {facility_code}")
        demographics = demog_base_schema.empty()
    
    return demographics
        

def query_ckd(session: Session, facility_code: str, end: dt.datetime, start: dt.datetime):
    return 