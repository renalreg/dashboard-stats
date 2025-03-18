"""
Pydantic classes for statistics which generate network graphs.
"""

from typing import List, Optional
from pydantic import Field

from ukrdc_stats.models.base import JSONModel


class NetworkMetaData(JSONModel):
    """Generic class to hold the metadata for data/stats with a network like structure.
    this is used to generate api calls for sankey diagrams
    """

    title: str = Field(..., description="Title of plot or statistic", max_length=40)
    summary: str = Field(..., description="Summary of plot", max_length=100)
    description: str = Field(
        ..., description="In depth description of how statistics are calculated"
    )
    total_population: Optional[int] = Field(
        None, description="Size of patient population for calculated statistic"
    )


class Nodes(JSONModel):
    """Contains labels/names accosiated with each node in the network"""

    node_labels: Optional[List[str]] = None


class Connections(JSONModel):
    """Contains data to describe the links in a sankey diagram (network) these links
    (or edges) are described by three numbers where the link is coming from where it
    is going and the weight"""

    source: List[str] = Field(..., description="index of connection source")
    target: List[str] = Field(..., description="index of connection target")
    value: List[str] = Field(..., description="weight of connection")


class LabelledNetwork(JSONModel):
    metadata: NetworkMetaData = Field(
        ..., description="Meta data containing title description etc"
    )
    node: Nodes = Field(..., description="Information on the nodes of the network")
    link: Connections = Field(..., description="Information on the network links")
