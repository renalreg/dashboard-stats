"""
This module contains data classes for the output of statistics models.
Each class or group will be accosiated with JSON schema for plotly.
For example the class pie is designed to naturally produce the schema for a plotly pie chart.
"""

from typing import List
from dataclasses import dataclass


@dataclass
class Layout:
    title: str


@dataclass
class Data:
    labels: List[str]
    values: List[int]


@dataclass
class Bar:
    data: Data
    layout: Layout


@dataclass
class BarList:
    """
    For returning a list of bar charts for a fixed population
    """

    pop: int
    bars: List[Bar]
