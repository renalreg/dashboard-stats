"""
Pydantic classes for statistics which generate network graphs.
"""

from typing import List, Optional

from pydantic import BaseModel


class NetworkMetaData(BaseModel):
    """Generic class to hold the metadata for data/stats with a network like structure.
    this is used to generate api calls for sankey diagrams
    """

    title: str
    summary: str
    description: str
    total_population: Optional[int] = None


class Nodes(BaseModel):
    """Contains labels/names accosiated with each node in the network"""

    node_labels: Optional[List[str]] = None


class Vertices(BaseModel):
    """Contains data to create vertices connecting each of the nodes"""

    source: List[str]
    target: List[str]
    value: List[str]


class LabelledNetwork(BaseModel):
    metadata: NetworkMetaData
    node: Nodes
    link: Vertices
