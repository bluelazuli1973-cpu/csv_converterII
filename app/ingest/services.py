import re
import pandas as pd


REQUIRED_COLUMNS = ["date", "metric", "value"]

REQUIRED_COLUMNS = [
    "Radnummer",
    "Clearingnummer",
    "Kontonummer",
    "Produkt",
    "Valuta",
    "Bokföringsdag",
    "Transaktionsdag",
    "Valutadag",
    "Referens",
    "Beskrivning",
    "Belopp",
    "Bokfört saldo",
]


def _parse_swedish_number(x) -> float | None:
    """
    Accepts typical Swedish/European number formats:
      - "1 234,56"
      - "1234,56"
      - "1234.56"
      - "-99,00"
    Returns float or None if blank.
    """
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None

    s = s.replace("\u00A0", " ")  # non-breaking space
    s = s.replace(" ", "")        # remove thousand separators spaces
    s = s.replace(",", ".")       # decimal comma -> dot

    # Keep digits, one leading '-', and dot
    if not re.fullmatch(r"-?\d+(\.\d+)?", s):
        raise ValueError(f"Invalid number: {x!r}")
    return float(s)

def parse_csv_to_dataframe(file_storage) -> pd.DataFrame:
    """
    Reads uploaded CSV into a dataframe and validates schema.
    """
    # Try UTF-8 first; many Swedish exports are UTF-8 or cp1252.
    # Pandas will raise if it can't decode; we can extend this if needed.
    df = pd.read_csv(file_storage)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}. Expected {REQUIRED_COLUMNS}")

    df = df[REQUIRED_COLUMNS].copy()

    # Parse dates (allow blank)
    for col in ["Bokföringsdag", "Transaktionsdag", "Valutadag"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    # Parse numbers
    df["Belopp"] = df["Belopp"].map(_parse_swedish_number)
    df["Bokfört saldo"] = df["Bokfört saldo"].map(_parse_swedish_number)

    # Required fields checks
    if df["Radnummer"].isna().any():
        raise ValueError("Column 'Radnummer' contains empty values.")
    if df["Clearingnummer"].astype(str).str.strip().eq("").any():
        raise ValueError("Column 'Clearingnummer' contains empty values.")
    if df["Kontonummer"].astype(str).str.strip().eq("").any():
        raise ValueError("Column 'Kontonummer' contains empty values.")
    if df["Belopp"].isna().any():
        raise ValueError("Column 'Belopp' contains empty/invalid values.")

    return df

def parse_csv_to_dataframeII(file_storage) -> pd.DataFrame:
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
