from ukrdc_stats.utils import age_from_dob, age_from_dob_exact, dob_cutoff_from_age
import datetime as dt


def test_age_from_dob():
    age = age_from_dob(dt.datetime(2022, 1, 1), dt.datetime(2021, 1, 1))
    assert age == 1

    age = age_from_dob(dt.datetime(2022, 1, 1), dt.datetime(2021, 1, 2))
    assert age == 0

    age_leap = age_from_dob(dt.datetime(2022, 2, 28), dt.datetime(2020, 2, 29))
    assert age_leap == 2
