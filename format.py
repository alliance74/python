import pandas as pd

# 1. Load the scraped data
df = pd.read_csv('RCA_Books_Final.csv')

# 2. Cleanup
# Convert ISBN to string without the .0 at the end
def format_isbn(val):
    if pd.isna(val) or val == 'N/A':
        return 'N/A'
    # Remove scientific notation and decimals
    return '{:.0f}'.format(float(val))

df['ISBN'] = df['ISBN'].apply(format_isbn)

# Remove the 'Unnamed: 0' column if it exists
if 'Unnamed: 0' in df.columns:
    df = df.drop(columns=['Unnamed: 0'])

# 3. Export to Excel (The "Spreadsheet")
output_excel = "RCA_Books_Formatted.xlsx"
df.to_excel(output_excel, index=False)

# 4. Export to JSON (The "Data Stylesheet" for your React app)
output_json = "books_data.json"
df.to_json(output_json, orient='records', indent=4)

print(f"Done! Created:\n1. {output_excel} (For reporting)\n2. {output_json} (For your web project)")