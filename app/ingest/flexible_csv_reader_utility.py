import csv
import io
from difflib import SequenceMatcher

import pandas as pd


def _read_all_bytes(source) -> bytes:
    """
    Accepts either a filesystem path (str/pathlike) or a file-like object.
    Returns file content as bytes.
    """
    if hasattr(source, "read"):
        data = source.read()
        return data if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8", errors="replace")
    with open(source, "rb") as f:
        return f.read()


def _sniff_delimiter(text_sample: str, fallback=(",", ";", "\t", "|")) -> str | None:
    try:
        dialect = csv.Sniffer().sniff(text_sample, delimiters="".join(fallback))
        return dialect.delimiter
    except csv.Error:
        return None


def read_flexible_csv(source) -> pd.DataFrame:
    """
    Reads a CSV from a path or file-like object with flexible encoding+delimiter handling.
    Raises ValueError with a useful message if it cannot parse.
    """
    raw = _read_all_bytes(source)
    if not raw:
        raise ValueError("CSV is empty.")

    encodings_to_try = ("utf-8-sig", "utf-8", "cp1252", "latin1")
    delimiters_to_try = [",", ";", "\t", "|"]

    last_error: Exception | None = None

    for enc in encodings_to_try:
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError as e:
            last_error = e
            continue

        # Use a small sample for delimiter sniffing
        sample = text[:50_000]
        sniffed = _sniff_delimiter(sample, fallback=tuple(delimiters_to_try))
        delimiter_order = ([sniffed] if sniffed else []) + [d for d in delimiters_to_try if d != sniffed]

        for delim in delimiter_order:
            try:
                df = pd.read_csv(io.StringIO(text), sep=delim)
                # Heuristic: a real CSV should produce more than 1 column
                if len(df.columns) > 1:
                    return df
            except (pd.errors.ParserError, UnicodeError, ValueError) as e:
                last_error = e
                continue

    raise ValueError(
        "Could not decode/parse the CSV. "
        "If the file comes from Excel on Windows, try exporting/saving it as 'CSV UTF-8'."
    ) from last_error


def normalize_columns(df: pd.DataFrame, field_mapping: dict[str, list[str]], threshold: float = 0.80) -> pd.DataFrame:
    """
    Map columns to standard names using stdlib fuzzy matching (no external deps).
    """
    def similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    column_map: dict[str, str] = {}

    for col in df.columns:
        col_norm = str(col).lower().strip()
        best_standard = None
        best_score = 0.0

        for standard_name, variants in field_mapping.items():
            for v in variants:
                score = similarity(col_norm, str(v).lower().strip())
                if score > best_score:
                    best_score = score
                    best_standard = standard_name

        if best_standard is not None and best_score >= threshold:
            column_map[col] = best_standard

    return df.rename(columns=column_map)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # Strip whitespace from all string columns
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    # Standardize date formats if present
    date_columns = {"date", "created_at", "timestamp"}
    for col in df.columns:
        if str(col).lower() in date_columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Remove duplicates
    df = df.drop_duplicates()

    # Drop rows where all values are null
    df = df.dropna(how="all")

    return df
