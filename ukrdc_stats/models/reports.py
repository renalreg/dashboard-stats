from ukrdc_stats.models.base import JSONModel
from ukrdc_stats.models.generic_2d import BaseTable


class CohortReport(JSONModel):
    description: str
    cohort: str
    population: int
    table: BaseTable
