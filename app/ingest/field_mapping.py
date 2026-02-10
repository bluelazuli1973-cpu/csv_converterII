from flexible_csv_reader_utility import read_whole_line_quoted_csv, normalize_columns, clean_data

field_mapping = {
    'email': ['email', 'e-mail', 'email_address'],
    'name': ['name', 'full_name', 'customer_name'],
    'phone': ['phone', 'telephone', 'tel'],
    'amount': ['Belopp', 'Priset', 'amount'],
    'date': ['Datum', 'date', 'dag'],
    'currency': ['Valuta', 'currency'],
    'reference': ['reference', 'ref', 'reference_number','Referens'],
    'description': ['description', 'Beskrivning', 'description_of_transaction']
}

# Process the CSV
df = read_whole_line_quoted_csv("Transaktioner_2026-01-07_12-01-44.csv",skip_first_row=True)
print("before selecting cols")
print(df.head())
df = normalize_columns(df, field_mapping)
df = clean_data(df)

# Keep only the columns you want
standard_columns = list(field_mapping.keys())
df = df[[col for col in standard_columns if col in df.columns]]
print("after selecting cols")
print(df.head())
print(df.columns)

# Export
df.to_csv('normalized_output2.csv', index=False)