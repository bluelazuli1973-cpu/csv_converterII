import re
import tempfile
import os
import pandas as pd
from app.ingest.flexible_csv_reader_utility import read_whole_line_quoted_csv, normalize_columns, clean_data

from app.ai_agent_models import ensure_category_model
import joblib


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

_CATEGORY_MODEL = None


def _load_category_model():
    """
    Loads the trained sklearn Pipeline used for category prediction.
    Cached in-process so we don't reload the model on every request.
    """
    global _CATEGORY_MODEL
    if _CATEGORY_MODEL is not None:
        return _CATEGORY_MODEL

    model_path = ensure_category_model()
    # ensure_category_model() returns the preferred .joblib path; if your training code
    # ever falls back to .pkl, it should still be loadable by joblib as well.
    _CATEGORY_MODEL = joblib.load(model_path)
    return _CATEGORY_MODEL


def _build_category_text(df: pd.DataFrame) -> pd.Series:
    """
    Build the text input expected by the trained model.
    Keep it simple and robust: concatenate description + reference.
    """
    desc = df.get("description", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str)
    ref = df.get("reference", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str)
    text = (desc.str.strip() + " " + ref.str.strip()).str.strip()
    return text


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


def derive_transaction_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived transaction fields used by the app/db.

    Option A:
      - keep df["amount"] signed
      - expense if amount < 0, otherwise income

    Also derives:
      - category (predicted by trained model)
      - category_confidence (max probability, if model supports predict_proba)

    Returns a new DataFrame (does not mutate the caller's df).
    """
    df = df.copy()

    if "amount" not in df.columns:
        raise ValueError("Cannot derive fields: missing required column 'amount'.")

    if df["amount"].isna().any():
        raise ValueError("Cannot derive fields: column 'amount' contains empty/invalid values.")

    df["is_expense"] = df["amount"] < 0

    # --- category prediction ---
    # Requires at least one text field to be present; we can still run with blanks,
    # but you'll likely want description/reference in your input CSV.
    texts = _build_category_text(df)

    model = _load_category_model()
    df["category"] = model.predict(texts.tolist())

    # Optional confidence if supported by the sklearn estimator
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(texts.tolist())
        df["category_confidence"] = proba.max(axis=1)
    else:
        df["category_confidence"] = pd.NA

    return df


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

        df = derive_transaction_fields(df)
        return df

    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                # If something still holds the file open, avoid masking the real error
                pass