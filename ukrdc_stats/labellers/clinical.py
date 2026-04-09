import pandas as pd
from ukrdc_stats.utils.database import get_archive_sessionmaker
from ukrdc_stats.utils.query import pid_ni_map
from ukrdc_stats.labellers.query import query_careplanning


def prevalent_careplanning(session, cohort, prevalence_date, assessment_type = "TPLTAssess")->pd.DataFrame:
    """
    Function labels a cohort of patients with the care planning assessment data
    based on a point of time.
    
    Args:
        session (_type_): _description_
        cohort (_type_): _description_
        prevalence_date (_type_): _description_
        assessment_type (str, optional): _description_. Defaults to "TPLTAssess".

    Raises:
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    
    if assessment_type not in ["TPLTassess", "KRTassess"]:
        raise ValueError("assessment_type must be either 'TPLTassess' or 'KRTassess'")

    if "pid" not in cohort.columns: 
        raise ValueError("cohort must contain 'pid' column")
    
    if "sendingfacility" not in cohort.columns:
        raise ValueError("cohort must contain 'sendingfacility' column")
    
    archive_sessionmaker = get_archive_sessionmaker(session)
    sending_facilities = cohort["sendingfacility"].unique().tolist()
    
    with archive_sessionmaker() as archive_session:
        careplanning_data = query_careplanning(
            archive_session, 
            sending_facilities, 
            prevalence_date
        )

    # Map patient IDs using pid_ni_map
    pid_map = pid_ni_map(session, sending_facilities)
    careplanning_data = careplanning_data.merge(
        pid_map,
        on=["patientid", "organization"],
        how="left",
    )

    careplanning_data = careplanning_data[careplanning_data["assessmenttypecode"] == assessment_type]    
    careplanning_data = careplanning_data[["pid", "assessmenttypecode", "assessmentstart", "assessmentend", "assessmentoutcomecode"]]
    careplanning_data["assessmentoutcome"] = careplanning_data["assessmentoutcomecode"].map(
        {"1": "Unsuitable", "2": "In-progress", "3": "Suitable"}
    ).fillna("Other")  

    # join careplanning to cohort
    cohort = cohort.merge(
        careplanning_data,
        on="pid",
        how="left"
    )
    cohort["assessmentoutcome"] = cohort["assessmentoutcome"].fillna("No assessment")

    return cohort