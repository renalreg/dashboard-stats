# Dashboard Statistics Library

Library for generating statistics for the ukrdc dashboard

[![Test](https://github.com/renalreg/dashboard-stats/actions/workflows/main.yml/badge.svg)](https://github.com/renalreg/dashboard-stats/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/renalreg/dashboard-stats/branch/master/graph/badge.svg?token=Ay8mk0zrKj)](https://codecov.io/gh/renalreg/dashboard-stats)

## Developer notes

### Installation

```bash
poetry install
```

### Iterating version numbers

The library should follow [semantic versioning](https://semver.org/).

[Use Poetry to set the application version.](https://python-poetry.org/docs/cli/#version)

E.g. `poetry version patch` for fix releases, `poetry version minor` for new functionality releases, or `poetry version major` for breaking-change releases.

### Running the demo notebooks

Install additional demo notebook dependencies with

```bash
poetry install --with demo
```
