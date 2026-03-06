"""
Version 3.0.0 of dashboard stats introduces pydantic style schemas the 
dataframes which are integral to the dashboard stats library the purpose of 
this change is to introduce better type checking and try and eliminate some of
the errors which arise from dataframes not having the expected columns.

In the first instance the schema will just look a type but pandera provides
many much more sophisticated options here.
"""
import pandera.pandas as pa
from pandera.typing import Series


class krt_base_schema(pa.DataFrameModel):
    # Core columns from base cohort query
    pid: Series[str]
    ukrdcid: Series[str]
    sendingfacility: Series[str]
    healthcarefacilitycode: Series[str] = pa.Field(nullable=True)
    admitreasoncode: Series[str]
    admitreasoncodestd: Series[str]
    admissionsourcecode: Series[str] = pa.Field(nullable=True)
    admissionsourcecodestd: Series[str] = pa.Field(nullable=True)
    qbl05: Series[str] = pa.Field(nullable=True)
    hdp04: Series[str] = pa.Field(nullable=True)
    dischargereasoncode: Series[str] = pa.Field(nullable=True)
    dischargereasoncodestd: Series[str] = pa.Field(nullable=True)
    dischargelocationcode: Series[str] = pa.Field(nullable=True)
    dischargelocationcodestd: Series[str] = pa.Field(nullable=True)
    registry_code_type: Series[str]
    deathtime: Series[pa.DateTime] = pa.Field(nullable=True)
    fromtime: Series[pa.DateTime]
    totime: Series[pa.DateTime] = pa.Field(nullable=True)
    ckd_centre: Series[str] = pa.Field(nullable=True)
    historic_tx: Series[bool]

    class Config:
        coerce = True

class demog_base_schema(pa.DataFrameModel):
    pid: Series[str]
    ukrdcid: Series[str]
    sendingfacility: Series[str]
    gender: Series[str] = pa.Field(nullable=True)
    ethnic_group: Series[str] = pa.Field(nullable=True)
    birth_time: Series[pa.DateTime] = pa.Field(nullable=True)
    deathtime: Series[pa.DateTime] = pa.Field(nullable=True)
    
    class Config:
        coerce = True
    