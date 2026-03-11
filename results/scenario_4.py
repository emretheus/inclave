import pandas as pd

# Function to read and process the CSV file
def process_csv(csv_path):
    try:
        # Read the CSV file with appropriate data types
        df = pd.read_csv(csv_path, parse_dates=['date'], dtype={'discount': 'float64'})
        
        # Group by city and calculate total revenue per city
        result = df.groupby('city')['revenue'].sum().reset_index()
        
        return result
    
    except FileNotFoundError:
        print(f"File not found: {csv_path}")
    except pd.errors.EmptyDataError:
        print("No data in the file.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
if __name__ == "__main__":
    csv_path = 'sales_data.csv'  # Replace with your actual CSV file path
    result = process_csv(csv_path)
    if result is not None:
        print(result)
