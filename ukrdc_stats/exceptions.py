"""
Exceptions for the UKRDC Statistics API
"""


class NoCohortError(ValueError):
    pass


class EmptyCohortError(ValueError):
    pass


class NoTestsError(ValueError):
    pass
