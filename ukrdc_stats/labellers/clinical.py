import pandas as pd
from ukrdc_stats.utils.database import get_archive_sessionmaker
from ukrdc_stats.utils.query import pid_ni_map
from ukrdc_stats.labellers.query import query_careplanning, query_vascular_access
from ukrdc_stats.utils.data import VASCULAR_MAPPING

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

def eskd():
    pass

def vascular_access(cohort, session, cutoff_date, mode:str = "first"):

    all_access_data = []
    pids = cohort["pid"].unique().tolist()
    
    for i in range(0, len(pids), 100):
        chunk = pids[i:i + 100]
        chunk_data = query_vascular_access(session, chunk)
        all_access_data.append(chunk_data)
    
    if len(all_access_data) == 0:
        access_data = pd.DataFrame(columns=["pid", "procedure_time", "qhd20"])
    else:
        access_data = pd.concat(all_access_data)


    if mode == "first":  
        access_data = access_data[
            access_data["procedure_time"] < cutoff_date
        ].sort_values(by="procedure_time").drop_duplicates(
            subset="pid", keep="first"
        )
    else:
        raise Exception("Invalid or unsupported mode")
    
    # join access data to cohort
    cohort = cohort.merge(
        access_data,
        on="pid",
        how="left"
    )
    cohort.rename(columns={"procedure_time": "vascular_access_date", "qhd20": "access"}, inplace=True)
    cohort.loc[cohort["vascular_access_date"].isna(), "access"] = "Missing"

    return cohort