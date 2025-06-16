# Dashboard Statistics Library

Library for generating statistics for the UKRDC dashboard

[![Test](https://github.com/renalreg/dashboard-stats/actions/workflows/main.yml/badge.svg)](https://github.com/renalreg/dashboard-stats/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/renalreg/dashboard-stats/branch/master/graph/badge.svg?token=Ay8mk0zrKj)](https://codecov.io/gh/renalreg/dashboard-stats)

## Usage

See [PKG-README](./PKG-README.md) for user installation and usage.

## Developer notes
⚠️This is a public repository all script output should be pointed at the .do_not_commit directory at the root of this project to prevent accidental committing of data. Tox testing be run and passing before any commits of notebooks or other code.

### Installation

```bash
poetry install
```

### Iterating version numbers

The library should follow [semantic versioning](https://semver.org/).

[Use Poetry to set the package version.](https://python-poetry.org/docs/cli/#version)

E.g. `poetry version patch` for fix releases, `poetry version minor` for new functionality releases, or `poetry version major` for breaking-change releases.

### Packaging and Publishing

Publishing the library is handled automatically by GitHub Actions.
The published version includes only the core library files, metadata, and `PKG-README.md`.
Demo notebooks, and tests, are not included.

To publish a new release:

- Ensure all tests are passing on the `master` branch.
- Update the package version number (see above section) on the `master` branch, commit, and push.
- [Create a new GitHub release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) named after the version number, with a prefixed lowercase "v". E.g. `v1.0.0`
  - Above the release name, create a new tag identical to the release name
- Publish the release. GitHub Actions will ensure all tests pass, then publish the library to PyPI.

### Running the demo notebooks

Install additional demo notebook dependencies with

```bash
poetry install --with demo
```

### Code Structure

#### `models`

Generic reusable Pydantic models (e.g. for plot types)

#### `calculators`

API-stable stats calculators
