"""
Generic 3D/map data model for UKRDC stats
"""

from datetime import datetime
from typing import List, Union, Optional

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
    title: str
    summary: str
    description: str

    axis_titles: Optional[AxisLabel3d] = None


class TimeSeries3d(JSONModel):
    meta_data: Basic3dMetadata
    data: TimeSeries3dData
