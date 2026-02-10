import re
import tempfile
import os
import pandas as pd
from app.ingest.flexible_csv_reader_utility import read_whole_line_quoted_csv, normalize_columns, clean_data


REQUIRED_COLUMNS = ["date", "metric", "value"]

REQUIRED_COLUMNS = [
    "amount",
    "transactionday",
    "currency",
    "reference",
    "description"
]

FIELD_MAPPING = {
    'email': ['email', 'e-mail', 'email_address'],
    'name': ['name', 'full_name', 'customer_name'],
    'phone': ['phone', 'telephone', 'tel'],
    'amount': ['Belopp', 'Priset', 'amount'],
    'transactionday': ['Datum', 'date', 'Bokföringsdag'],
    'currency': ['Valuta', 'currency'],
    'reference': ['reference', 'ref', 'reference_number','Referens'],
    'description': ['description', 'Beskrivning', 'description_of_transaction']
}

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
    Saves FileStorage to a temp file to obtain a real filesystem path.
    """
    tmp_path = None
    try:
        # On Windows, use delete=False so we can reopen it by name.
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
            file_storage.save(tmp)  # FileStorage-friendly (doesn't rely on .read())

        #Reading the file into a dataframe
        df = read_whole_line_quoted_csv(
            tmp_path,
            skip_first_row=True,
            encoding="windows-1252",
            sep=",",
            usecols=[4, 5, 8, 9, 10],
        )
        # Normalizing the column names to a certain standard
        df = normalize_columns(df, FIELD_MAPPING)
        df = clean_data(df)

        # Keep only the columns you want
        standard_columns = list(FIELD_MAPPING.keys())
        df = df[[col for col in standard_columns if col in df.columns]]

        # Validate required columns
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}. Expected {REQUIRED_COLUMNS}")

        df = df[REQUIRED_COLUMNS].copy()

        # Parse dates (allow blank)
        for col in ["transactionday"]:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

        # Parse numbers
        df["amount"] = df["amount"].map(_parse_swedish_number)

        # Required fields checks
        if df["amount"].isna().any():
            raise ValueError("Column 'amount' contains empty/invalid values.")

        return df

    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                # If something still holds the file open, avoid masking the real error
                pass

