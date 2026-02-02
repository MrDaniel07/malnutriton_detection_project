import numpy as np
import pandas as pd


def generate_synthetic_data(n_samples=2000, random_state=42):
    """Generate synthetic pediatric data with a malnutrition label.

    The generator simulates common measurements used for early malnutrition
    screening (age, weight, height, MUAC, recent diarrhea, etc.) and
    produces a binary label `malnourished` computed from a logistic
    probability function. This is a prototype dataset for model
    development and demonstration only.
    """
    rng = np.random.RandomState(random_state)
    age_months = rng.randint(0, 60, size=n_samples)
    weight_kg = np.clip(rng.normal(10 + 0.2 * age_months, 2.0, size=n_samples), 2, 30)
    height_cm = np.clip(rng.normal(65 + 1.5 * age_months, 6.0, size=n_samples), 45, 140)
    muac = np.clip(rng.normal(13 + 0.02 * age_months, 1.5, size=n_samples), 7, 25)
    breastfeeding = rng.binomial(1, 0.6, size=n_samples)
    diarrhea = rng.binomial(1, 0.1, size=n_samples)
    immunizations = rng.randint(0, 8, size=n_samples)
    household_income = np.clip(rng.normal(50000, 30000, size=n_samples), 1000, 200000)
    maternal_education = rng.randint(0, 16, size=n_samples)

    # A simple logistic function to simulate malnutrition risk.
    logits = (
        -2.5
        + -0.02 * age_months
        + -0.15 * (weight_kg - (age_months * 0.2 + 10))
        + -0.12 * (muac - 13)
        + -0.5 * breastfeeding
        + 0.8 * diarrhea
        + -0.03 * immunizations
        + -0.00001 * household_income
        + -0.05 * maternal_education
    )
    prob = 1.0 / (1.0 + np.exp(-logits))
    malnourished = (rng.rand(n_samples) < prob).astype(int)

    df = pd.DataFrame(
        {
            "age_months": age_months,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "muac_cm": muac,
            "breastfeeding": breastfeeding,
            "recent_diarrhea": diarrhea,
            "immunizations": immunizations,
            "household_income": household_income,
            "maternal_education_years": maternal_education,
            "malnourished": malnourished,
        }
    )
    return df


def load_csv(path_or_buffer):
    """Load a CSV into a DataFrame and ensure expected columns exist.

    This helper is minimal — it returns the DataFrame and the caller
    should validate required columns for modelling.
    """
    return pd.read_csv(path_or_buffer)
