# Dashboard Statistics Library

Library for generating statistics for the UKRDC dashboard

## Installation

`pip install ukrdc-stats`

## Basic usage

Statistics calculations require an SQLAlchemy session with a connection to the UKRDC3 database.
In this example, we use `ukrdc3_session`, and calculate for the unit code "TEST_UNIT".

```python
from ukrdc_stats import DemographicStatsCalculator

demographics = DemographicStatsCalculator(ukrdc3, "TEST_UNIT").extract_stats()
```

Each calculator returns multiple stats from the same cohort, and each of those includes basic metadata required for rendering and plotting the data.
