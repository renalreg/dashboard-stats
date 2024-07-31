"""
Tests/debug helpers designed to be run with a real database connection. We can
also use them for verification against known ukrdc data.
"""

from sqlalchemy.orm import Session 
from ukrdc_stats.calculators.dialysis import DialysisStatsCalculator
import datetime as dt

def test_dialysis_base_cohort(ukrdc3_real_db_session:Session):
    if ukrdc3_real_db_session is not None:
        calculator = DialysisStatsCalculator(
            ukrdc3_real_db_session, 
            "RNJ00", 
            from_time=dt.datetime(2021, 12, 31), 
            to_time=dt.datetime(2022, 12, 31)
        )

        dialysis_stats = calculator.extract_stats()