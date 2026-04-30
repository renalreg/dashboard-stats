import pandas as pd
import datetime as dt
from ukrdc_stats.exceptions import MissingColumnError



def age(
    patient_cohort: pd.DataFrame,
    reference_date: dt.datetime,
    bins: dict = {
        "bins": [0, 18, 35, 55, 75, 150],
        "labels": ["Under 18", "18-34", "35-54", "55-74", "75+"],
    },
) -> pd.DataFrame:
    """
    Calculate age groups for a patient cohort.

    Args:
        patient_cohort (pd.DataFrame): DataFrame containing patient data with 'birth_date' column.
        reference_date (dt.datetime): Date to calculate ages from.
        bins (_type_, optional): Dictionary with 'bins' and 'labels' keys. Defaults to { "bins" : [0, 18, 35, 55, 75, 150], "labels" :["Under 18", "18-34", "35-54", "55-74", ">=75"] }.
    """

    if "birthtime" not in patient_cohort.columns:
        raise MissingColumnError("Patient cohort must contain 'birthtime' column")

    if "age" in patient_cohort.columns:
        raise ValueError("Cohort already labelled with age")

    patient_cohort["decimalage"] = (
        reference_date - patient_cohort["birthtime"]
    ).dt.days / 365.25
    patient_cohort["age"] = pd.cut(
        patient_cohort["decimalage"],
        bins=bins["bins"],
        labels=bins["labels"],
        include_lowest=True,
    )

    return patient_cohort


def adult_paed(patient_cohort: pd.DataFrame) -> pd.DataFrame:
    """
    Placeholder to classify patients as adult or paediatric on age.
    Strictly the definition is more specific and involves looking at the
    treatment centre.

    Args:
        patient_cohort (pd.DataFrame): DataFrame containing patient data with 'age' column.
    """
    if "age" not in patient_cohort.columns:
        raise MissingColumnError("Patient cohort must contain 'age' column")

    patient_cohort["adult_paed"] = pd.NA
    patient_cohort.loc[patient_cohort["age"] == "Under 18", "adult_paed"] = "Paediatric"
    patient_cohort.loc[patient_cohort["age"] != "Under 18", "adult_paed"] = "Adult"

    return patient_cohort



