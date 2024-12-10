"""
Functions to calculate patient cohort statistics.
Pydantic classes to return nice plotly friendly output.
Utility functions to handle bitty things.
"""

from ukrdc_stats.calculators.demographics import DemographicStatsCalculator
from ukrdc_stats.calculators.krt import KRTStatsCalculator

__all__ = ["DemographicStatsCalculator", "KRTStatsCalculator"]
