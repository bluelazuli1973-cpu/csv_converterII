import csv
import io
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

"""
read_whole_line_quoted_csv: Can handle swedish csv where each line is quoted
"""
def read_whole_line_quoted_csv(path: str, *, encoding: str = "windows-1252", sep: str = ",") -> pd.DataFrame:
    with open(path, "r", encoding=encoding, newline="") as f:
        lines = f.read().splitlines()

    repaired = []
    for i, line in enumerate(lines):
        s = line.strip()
        if i > 0 and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            # Remove the outer quotes; keep inner content
            s = s[1:-1]
        repaired.append(s)

    return pd.read_csv(io.StringIO("\n".join(repaired)), sep=sep)

# Example:
# df = read_whole_line_quoted_csv("output.csv")
# print(df.columns, df.head())

def strip_quotes_from_csv(input_file, output_file,enc='windows-1252'):
    """
    Read a CSV file and remove all double quotes from the data,
    then write to a new CSV file.

    Args:
        input_file: Path to the input CSV file
        output_file: Path to the output CSV file
    """
    with open(input_file, 'r', encoding=enc) as infile, \
            open(output_file, 'w', encoding=enc, newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL, escapechar='\\')

        for row in reader:
            # Strip quotes from each field in the row
            cleaned_row = [field.replace('"', '') for field in row]
            writer.writerow(cleaned_row)


# Example usage:
# strip_quotes_from_csv('input.csv', 'output.csv')

def _read_all_bytes(source) -> bytes:
    """
    Accepts either a filesystem path (str/pathlike) or a file-like object.
    Returns file content as bytes.
    """
    if hasattr(source, "read"):
        try:
            if hasattr(source, "seek"):
                source.seek(0)
        except Exception:
            pass

        data = source.read()
        return data if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8", errors="replace")

    with open(source, "rb") as f:
        return f.read()


def _extract_excel_sep_hint(text: str) -> tuple[str | None, int]:
    """
    Detect Excel-style 'sep=;' hint on the first non-empty line.
    Returns: (sep_hint or None, skiprows)
    """
    # Normalize BOM in case decoding produced it
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")

    lines = text.splitlines()
    for i, ln in enumerate(lines[:5]):  # only need the first few lines
        s = ln.strip()
        if not s:
            continue
        if s.lower().startswith("sep=") and len(s) >= 5:
            return s[4], i + 1  # sep char, and skip rows up to and including this line
        break
    return None, 0


def read_csv_explicit(
    source,
    *,
    encoding: str = "windows-1252",
    sep: str = ",",
    header: int | None = 0,
    quotechar: str = '"',
) -> pd.DataFrame:
    """
    Read a CSV using explicit encoding + separator (no guessing).
    Also supports Excel 'sep=;' hint line by auto-skipping it.

    If parsing still results in 1 column, raises a helpful error.
    """
    raw = _read_all_bytes(source)
    if not raw:
        raise ValueError("CSV is empty.")

    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError as e:
        raise ValueError(
            f"Could not decode CSV with encoding={encoding!r}. "
            "Common encodings: 'windows-1252' (Excel on Windows), 'utf-8-sig'."
        ) from e

    sep_hint, skiprows = _extract_excel_sep_hint(text)
    if sep_hint is not None:
        # If the file declares its delimiter, trust it.
        sep = sep_hint

    df = pd.read_csv(
        io.StringIO(text),
        sep=sep,
        header=header,
        skiprows=skiprows,
        engine="python",
        quotechar=quotechar,
        doublequote=True,
        skip_blank_lines=True,
    )
    print("readin csv with sep =", sep)
    print(df.head())

    # If we still only got one column, it's almost certainly the wrong sep (or not delimiter-separated data).
    if len(df.columns) == 1:
        col0 = df.columns[0]
        sample_vals = df[col0].dropna().astype(str).head(20).tolist()

        # If separator appears inside the values, we're not splitting correctly.
        if any(sep in v for v in sample_vals):
            raise ValueError(
                "Still parsed into a single column.\n"
                f"Detected/used sep={sep!r}, encoding={encoding!r}, skipped_rows={skiprows}.\n"
                "This usually means the real delimiter is different, or the file is not a normal CSV.\n"
                "Next step: open the file in a text editor and check what character is between fields "
                "(common: ';', ',', '\\t')."
            )

    return df


# ... existing code ...
def normalize_columns(df: pd.DataFrame, field_mapping: dict[str, list[str]], threshold: float = 0.80) -> pd.DataFrame:
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
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    date_columns = {"date", "created_at", "timestamp"}
    for col in df.columns:
        if str(col).lower() in date_columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df = df.drop_duplicates()
    df = df.dropna(how="all")
    return df