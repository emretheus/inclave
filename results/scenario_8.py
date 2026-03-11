import pandas as pd

# Function to read and process the CSV file
def process_and_export(csv_path):
    try:
        # Read the CSV file with appropriate data types
        df = pd.read_csv(csv_path, parse_dates=['date'])
        
        # Drop duplicate rows
        df.drop_duplicates(inplace=True)
        
        # Export to Excel with sheet name 'Sales'
        df.to_excel('output.xlsx', sheet_name='Sales', index=False)
        
        print("Data exported successfully to output.xlsx")
    except FileNotFoundError:
        print(f"Error: The file {csv_path} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
csv_path = 'sales_data.csv'
process_and_export(csv_path)
