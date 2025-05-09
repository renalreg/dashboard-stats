"""
Generic 2D data model for UKRDC stats
"""

import csv

import pandas as pd

from datetime import datetime
from typing import List, Optional, Any
from pydantic import Field

from ukrdc_stats.models.base import JSONModel

Number = int | float | None
RowData = List[Any]


# Generics
class AxisLabels2d(JSONModel):
    """
    Generic class for any x/y axis labels
    """

    x: Optional[str] = None
    y: Optional[str] = None


class Basic2dMetadata(JSONModel):
    """
    Stats/plot metadata generic to all 2D data sets
    """

    title: str = Field(..., description="Title of plot or statistics", max_length=40)
    summary: str = Field(
        ...,
        description="Summary of what the plot or statistic is trying to achieve",
        max_length=100,
    )
    description: str = Field(
        ...,
        description="In depth description of what exactly is represented and how it has been calculated",
    )
    axis_titles: Optional[AxisLabels2d] = Field(
        None, description="x and y labels for data"
    )
    population_size: Optional[int] = Field(
        None,
        description="Total population size of cohort used for statistic e.g total number of patients in pie chart",
    )


# Time series


class TimeSeries2dData(JSONModel):
    """
    x-y data for a time series plot
    """

    x: List[datetime] = Field(..., description="datatime labels for datapoints")
    y: List[Number] = Field(..., description="Datapoints")
    error_y: Optional[List[Number]] = Field(
        None, description="error bars associated with datapoints"
    )


class TimeSeries2dMetadata(Basic2dMetadata):
    """
    Metadata for a time series plot.

    x-axis is always a datetime, so no x-axis units are required.
    """

    units_y: Optional[str] = Field(None, description="units of y datapoints")


class TimeSeries2d(JSONModel):
    """
    Return data class for a time series plot
    """

    metadata: TimeSeries2dMetadata = Field(
        ...,
        description="Metadata including title and description for 2D time series dataset",
    )
    data: TimeSeries2dData = Field(
        ..., description="2D dataset of timestamped datapoints"
    )


# Numeric


class Numeric2dData(JSONModel):
    """
    x-y data for a numeric plot
    """

    x: List[Number] = Field(..., description="Numeric x data points")
    y: List[Number] = Field(..., description="Y data points")
    error_x: Optional[List[Number]] = Field(
        None, description="Uncertainty associated with x data points"
    )
    error_y: Optional[List[Number]] = Field(
        None, description="Uncertainty associated with y data points"
    )


class Numeric2dMetadata(Basic2dMetadata):
    """
    Metadata for a numeric plot.

    We may want units for both x and y values, so both are optional here.
    """

    units_x: Optional[str] = Field(None, description="Units of y datapoints")
    units_y: Optional[str] = Field(None, description="Units of x datapoints")


class Numeric2d(JSONModel):
    """
    Return data class for a numeric plot
    """

    metadata: Numeric2dMetadata = Field(
        ...,
        description="Metadata including title and description for 2D time series dataset",
    )
    data: Numeric2dData = Field(
        ..., description="2D data containing x and y as numbers"
    )


class Labelled2dData(JSONModel):
    """
    x-y data for a labelled plot
    """

    x: List[str] = Field(..., description="list of x data points")
    y: List[Number] = Field(..., description="list of y data points")
    error_y: Optional[List[Number]] = Field(
        None, description="Uncertainty in y data points"
    )


class Labelled2dMetadata(Basic2dMetadata):
    """
    Metadata for a labelled plot.

    x-axis is always a string/label, so no x-axis units are required.
    y-axis is numeric, and so units are optional here.
    """

    coding_standard_x: Optional[str] = Field(
        None, description="UKRDC coding standard of x data points"
    )  # I wonder if this should be a list otherwise are assuming coding standard remains constant
    units_y: Optional[str] = Field(None, description="Units of y data point")


class Labelled2d(JSONModel):
    """
    Return data class for a labelled plot
    """

    metadata: Labelled2dMetadata = Field(
        ..., description="Metadata for 2D data consisting of label datapoint pairs"
    )
    data: Labelled2dData = Field(
        ..., description="2D data consisting of label datapoint pairs"
    )


class BaseTable(JSONModel):
    headers: List[str] = Field(
        ..., description="Column headers describing the data contained in each row"
    )

    rows: List[RowData] = Field(
        ..., description="Rows of the table containing the data"
    )
    # rows: List[str] = Field(
    #    ..., description="Rows of the table containing the data"
    # )

    def to_csv(
        self, file_path: str, blank_na: bool = True, metadata: str = None
    ) -> None:
        """
        Serializes the BaseTable to a CSV file.

        :param file_path: The path to the file where the CSV data will be written.
        """
        with open(file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            if metadata:
                csv_file.write(metadata)
            writer = csv.writer(csv_file)
            writer.writerow(self.headers)  # Write the headers
            for row in self.rows:
                writer.writerow(
                    [item if not pd.isna(item) else "" for item in row]
                    if blank_na
                    else row
                )

    def to_pandas(self) -> None:
        return pd.DataFrame(self.rows, columns=self.headers).astype("string")
