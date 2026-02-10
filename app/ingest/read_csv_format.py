import pandas as pd
from typing import Dict, Any

REQUIRED_COLUMNS_TYPE = {
    "Produkt":str,
    "Valuta":str,
#    "Transaktionsdag":"datetime64[ns]",
#    "Valutadag":"datetime64[ns]",
    "Referens":str,
    "Beskrivning":str,
    "Belopp":float
}


def load_and_convert_csv(
        csv_path: str,
        column_types: Dict[str, Any],
        **read_csv_kwargs
) -> pd.DataFrame:
    """
    Load a CSV file and convert columns to specified types.

    Parameters:
    -----------
    csv_path : str
        Path to the CSV file
    column_types : dict
        Dictionary mapping column names to their desired types
        Example: {'age': int, 'name': str, 'price': float, 'date': 'datetime64[ns]'}
    **read_csv_kwargs
        Additional keyword arguments to pass to pd.read_csv()

    Returns:
    --------
    pd.DataFrame
        DataFrame with only the specified columns and converted types

    Raises:
    -------
    FileNotFoundError
        If the CSV file doesn't exist
    ValueError
        If none of the specified columns exist in the CSV
    """
    # Read the CSV file
    df = pd.read_csv(csv_path, encoding='windows-1252', **read_csv_kwargs)


    # Find columns that exist in both the CSV and the dictionary
    existing_columns = [col for col in column_types.keys() if col in df.columns]

    if not existing_columns:
        raise ValueError(
            f"None of the specified columns {list(column_types.keys())} "
            f"were found in the CSV. Available columns: {list(df.columns)}"
        )

    # Keep only the columns specified in the dictionary
    df = df[existing_columns]

    # Convert each column to its specified type
    for col, dtype in column_types.items():
        if col in df.columns:
            try:
                df[col] = df[col].astype(dtype)
            except (ValueError, TypeError) as e:
                print(f"Warning: Could not convert column '{col}' to {dtype}. Error: {e}")

    return df


# Example usage:
"""if __name__ == "__main__":
    # Define column types
    column_mapping = {
        'user_id': int,
        'username': str,
        'age': int,
        'balance': float,
    }

    # Load and convert
    df = load_and_convert_csv('data.csv', column_mapping)
    print(df.dtypes)
    print(df.head())
"""