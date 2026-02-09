"""
cvsReadAndConvert is a module that can read csv files convert numbers and put result in a list of list structure
where the rows in the csv are sublists of the structure and the main list includes the rows making it a row and
column matrix
"""

def _auto_convert(value, na_values=None):
    """
    Convert a string value to int, float, bool, or None when appropriate.
    Returns the original string if no conversion applies.
    """
    if na_values is None:
        na_values = {"", "na", "n/a", "null", "none"}
    v = value.strip()
    # Missing values
    if v.lower() in na_values:
        return None
    # Booleans
    low = v.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    # Integers
    try:
        if v.startswith(("0x", "-0x")):
            # Hex integers
            return int(v, 16)
        return int(v)
    except ValueError:
        pass
    # Floats (including scientific notation)
    try:
        return float(v)
    except ValueError:
        pass
    # Default: return trimmed string
    return v


def read_csv_and_convert(filepath, skip_first_row=False, delimiter=",", convert_types=True, na_values=None):
    """
    Read a delimited text file into a list of lists.

    Args:
        filepath (str): Path to the file.
        skip_first_row (bool): If True, skip the first line (e.g., header).
        delimiter (str): Field separator (default ",").
        convert_types (bool): If True, auto-convert to int/float/bool/None.
        na_values (Iterable[str] | None): Values considered missing, e.g. {"", "NA"}.

    Returns:
        list[list[Any]]: Rows as lists of values with optional type conversion.
    """
    data = []
    na_set = set(na_values) if na_values is not None else None

    with open(filepath, "r") as file:
        if skip_first_row:
            next(file, None)  # Safely skip the first line if present

        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            fields = [cell.strip() for cell in stripped.split(delimiter)]
            if convert_types:
                row = [_auto_convert(cell, na_values=na_set) for cell in fields]
            else:
                row = fields
            # Skip completely empty rows (all None/empty)
            if not any(x is not None and str(x) != "" for x in row):
                continue
            data.append(row)

    return data


# Example:
# rows = read_csv("your_file.csv", skip_first_row=True, delimiter=";", convert_types=True, na_values={"", "NA", "N/A"})
# print(rows)
