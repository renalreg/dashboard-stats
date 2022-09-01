import datetime as dt


def age_from_dob(date: dt.date, dob: dt.date) -> int:
    """_summary_

    Args:
        date (datetime): Date to calculate age or time period from.
        dob (datetime): Date to calculate age or time period at.

    Returns:
        int: age or period in years
    """
    years_old: int

    # calculates age by common definition
    years_old = date.year - dob.year - 1
    try:
        year_birthday = dt.datetime(date.year, dob.month, dob.day)
    except ValueError:
        # exemption triggered for people with birthday on leap year if not a leap year
        year_birthday = dt.datetime(date.year, dob.month, dob.day - 1)

    if year_birthday <= date:
        years_old += 1

    return years_old
