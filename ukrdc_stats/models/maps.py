"""
Generic 3D/map data model for UKRDC stats
"""

from datetime import datetime
from typing import List, Union, Optional
from pydantic import Field

from .base import JSONModel

Number = Union[int, float]


class TimeSeries3dData(JSONModel):
    x: List[datetime]
    y: List[Number]
    z: List[Number]


class AxisLabel3d(JSONModel):
    x: Optional[str]
    y: Optional[str]
    z: Optional[str]


class Basic3dMetadata(JSONModel):
    """
    Meta data describing pydantic models for 3D data
    """

    title: str = Field(
        ..., description="Title of 3D data or stats group", max_length=40
    )
    summary: str = Field(
        ..., description="Short summary of stats being returned", max_length=100
    )
    description: str = Field(
        ...,
        description="Full length description detailing exactly how the statistics were calculated",
    )

    axis_titles: Optional[AxisLabel3d] = None


class TimeSeries3d(JSONModel):
    meta_data: Basic3dMetadata
    data: TimeSeries3dData
