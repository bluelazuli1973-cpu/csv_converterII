import pandas as pd


REQUIRED_COLUMNS = ["date", "metric", "value"]


def parse_csv_to_dataframe(file_storage) -> pd.DataFrame:
    """
    Reads uploaded CSV into a dataframe and validates schema.
    """
    df = pd.read_csv(file_storage)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}. Expected {REQUIRED_COLUMNS}")

    # Keep only required columns (avoid accidental extra columns for now)
    df = df[REQUIRED_COLUMNS].copy()

    # Parse types
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.date
    df["metric"] = df["metric"].astype(str).str.strip()
    df["value"] = pd.to_numeric(df["value"], errors="raise")

    # Basic sanity checks
    if df["metric"].eq("").any():
        raise ValueError("Column 'metric' contains empty values.")
    if df.isna().any().any():
        raise ValueError("CSV contains invalid/empty values after parsing.")

    return df
