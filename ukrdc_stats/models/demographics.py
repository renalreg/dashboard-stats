from typing import Optional

from pydantic import BaseModel

from ukrdc_stats.models.generic_2d import Labelled2d


class DemographicStatsMetadata(BaseModel):
    population: Optional[int] = None


class DemographicStats(BaseModel):
    gender: Labelled2d
    birth_country: Labelled2d
    primary_language: Labelled2d
    ethnic_group_code: Labelled2d

    metadata: DemographicStatsMetadata
