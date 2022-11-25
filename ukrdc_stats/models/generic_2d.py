"""
Generic 2D data model for UKRDC stats
"""

from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel

Number = Union[int, float, None]

# Generics


class AxisLabels2d(BaseModel):
    """
    Generic class for any x/y axis labels
    """

    x: Optional[str] = None
    y: Optional[str] = None


class Basic2dMetadata(BaseModel):
    """
    Stats/plot metadata generic to all 2D data sets
    """

    title: str
    summary: str
    description: str
    axis_titles: Optional[AxisLabels2d] = None


# Time series


class TimeSeries2dData(BaseModel):
    """
    x-y data for a time series plot
    """

    x: List[datetime]
    y: List[Number]
    error_y: Optional[List[Number]] = None


class TimeSeries2dMetadata(Basic2dMetadata):
    """
    Metadata for a time series plot.

    x-axis is always a datetime, so no x-axis units are required.
    """

    units_y: Optional[str] = None


class TimeSeries2d(BaseModel):
    """
    Return data class for a time series plot
    """

    metadata: TimeSeries2dMetadata
    data: TimeSeries2dData


# Numeric


class Numeric2dData(BaseModel):
    """
    x-y data for a numeric plot
    """

    x: List[Number]
    y: List[Number]
    error_x: Optional[List[Number]] = None
    error_y: Optional[List[Number]] = None


class Numeric2dMetadata(Basic2dMetadata):
    """
    Metadata for a numeric plot.

    We may want units for both x and y values, so both are optional here.
    """

    units_x: Optional[str] = None
    units_y: Optional[str] = None


class Numeric2d(BaseModel):
    """
    Return data class for a numeric plot
    """

    metadata: Numeric2dMetadata
    data: Numeric2dData


class Labelled2dData(BaseModel):
    """
    x-y data for a labelled plot
    """

    x: List[str]
    y: List[Number]
    error_y: Optional[List[Number]] = None


class Labelled2dMetadata(Basic2dMetadata):
    """
    Metadata for a labelled plot.

    x-axis is always a string/label, so no x-axis units are required.
    y-axis is numeric, and so units are optional here.
    """

    coding_standard_x: Optional[str] = None
    units_y: Optional[str] = None


class Labelled2d(BaseModel):
    """
    Return data class for a labelled plot
    """

    metadata: Labelled2dMetadata
    data: Labelled2dData
