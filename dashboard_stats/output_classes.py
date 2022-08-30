"""
This module contains the pydantic classes for the output of statistics models. Each class or group will be accosiated with JSON schema for plotly. For example the class pie is designed to naturally produce the schema for a plotly pie chart. 
"""

from pydantic import BaseModel
from typing import List


class layout(BaseModel):
    title: str


class data(BaseModel):
    labels: List[str]
    values: List[int]
    # type: 'pie'


class bar(BaseModel):
    data: data
    layout: layout


class bars(BaseModel):
    """
    For returning a list of bar charts for a fixed population
    """

    pop: int
    bar_list: List[bar]
