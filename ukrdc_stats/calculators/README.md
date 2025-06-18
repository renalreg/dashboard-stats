# UKRDC Stats Calculators

This folder holds statistics calculators for the UK Renal Registry Data Warehouse. These calculators extract and shape data from the UKRDC database to build reports and dashboards.

## Main Methods

The calculators have two key methods for working with patient data:

## 1. Extract Statistics

The `extract_stats` method pulls statistics from patient data:

```python
from sqlalchemy.orm import Session
from ukrdc_stats.calculators.demographics import DemographicStatsCalculator

# Create database session
session = Session(engine)

# Create a calculator instance
calculator = DemographicStatsCalculator(
    session=session,
    facility="ABC123"
)

# Extract statistics (automatically extracts patient cohort if needed)
stats = calculator.extract_stats(
    include_tracing=False,  # Whether to use NHS tracing records for death dates
    limit_to_ukrdc=True,    # Only include UKRDC records
    ukrr_expanded=False     # Use expanded UKRR inclusion criteria
)
```

### Return Models

Each calculator returns a specific Pydantic model:

#### DemographicsStats Model

```python
stats = DemographicsStats(
    gender=Labelled2d(...),       # Gender breakdown
    ethnic_group=Labelled2d(...), # Ethnicity breakdown
    age=Labelled2d(...),          # Ages of living patients
    metadata=DemographicsMetadata(population=1234)
)
```

#### KRTStats Model

Contains kidney replacement therapy modality breakdowns by timepoint.

#### CKDStats Model

Contains CKD stage breakdowns by timepoint.

### Histogram Format

All statistics are returned as `Labelled2d` objects:

```python
Labelled2d(
    metadata=Labelled2dMetadata(
        title="Gender Distribution",
        summary="Breakdown of patient gender identity codes",
        description="Description text",
        axis_titles=AxisLabels2d(x="Gender", y="No. of Patients")
    ),
    data=Labelled2dData(
        x=["Male", "Female", "Indeterminate", "Unknown"],  # Labels
        y=[100, 120, 5, 20]  # Count values
    )
)
```

## 2. Produce Report

The `produce_report` method gives you tabular data from the patient cohort:

```python
# After extract_patient_cohort() has been called:
population, table = calculator.produce_report(
    output_columns=["pid", "gender", "ethnic_group_code"],  # Columns to include
    input_filters=["gender == 'Male'", "age > 65"],        # Optional pandas query filters
    include_ni=True                                       # Include NHS numbers
)
```

### Report Output

Returns a tuple with:

1. `population` (int): Count of unique patients matching the filters
2. `table` (BaseTable): A Pydantic model containing:

```python
BaseTable(
    headers=["pid", "gender", "ethnic_group_code", "nhsno"],  # Column names
    rows=[["12345", "Male", "A", "9876543210"], ...]         # Row data
)
```

## Working with Returned Models

Here's how to unpack and work with the models returned by the calculators:

### Using DemographicsStats Models

```python
# Get demographic stats
stats = calculator.extract_stats()

# Access total population count
population_count = stats.metadata.population
print(f"Total patients: {population_count}")

# Get raw gender data
gender_labels = stats.gender.data.x  # ['Male', 'Female', 'Indeterminate', 'Unknown']
gender_counts = stats.gender.data.y   # [145, 158, 2, 12]

# Get chart title and axis labels
title = stats.gender.metadata.title   # "Gender Distribution"
x_axis = stats.gender.metadata.axis_titles.x  # "Gender"
y_axis = stats.gender.metadata.axis_titles.y  # "No. of Patients"

# Get ethnicity breakdown
ethnic_groups = stats.ethnic_group.data.x
ethnic_counts = stats.ethnic_group.data.y

# Create a dictionary for easy lookup
ethnic_data = dict(zip(ethnic_groups, ethnic_counts))
print(f"White British patients: {ethnic_data.get('White British', 0)}")

# Convert to JSON for API response or storage
json_data = stats.json(indent=2)
```

### Working with Report Tables

```python
# Get table report
population, table = calculator.produce_report(
    output_columns=["pid", "gender", "ethnic_group_code", "age"],
    input_filters=["age > 65"]
)

# Report can be exported to CSV directly
metadata = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
with open("report.csv", "w") as f:
    table.to_csv(f, metadata=metadata, blank_na=True)

# Convert to pandas DataFrame using the built-in method
df = table.to_pandas()

# Now we can use all the power of pandas
print(f"Total patients: {population}")
print(f"Average age: {df['age'].mean():.1f}")

# Get count by gender
gender_counts = df['gender'].value_counts()
print(f"Males: {gender_counts.get('Male', 0)}")
print(f"Females: {gender_counts.get('Female', 0)}")

# Calculate percentages
gender_pct = gender_counts / gender_counts.sum() * 100
print(f"Male percentage: {gender_pct.get('Male', 0):.1f}%")

# Filter for specific ethnicity and show counts
ethnic_counts = df['ethnic_group_code'].value_counts()
print(f"Patients in group A: {ethnic_counts.get('A', 0)}")
```

## Error Handling

Key error to handle:

```python
from ukrdc_stats.exceptions import NoCohortError

try:
    stats = calculator.extract_stats()
except NoCohortError:
    print("No patients found - check facility code or data feed")
```
