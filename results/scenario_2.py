import pandas as pd

# Function to load and process the CSV file
def process_csv(csv_path):
    try:
        # Load the CSV file in chunks to handle large files if necessary
        chunksize = 10000
        for chunk in pd.read_csv(csv_path, chunksize=chunksize):
            # Convert 'date' column to datetime
            chunk['date'] = pd.to_datetime(chunk['date'])
            
            # Fill null discount values with 0
            chunk['discount'].fillna(0, inplace=True)
            
            # Process the chunk (e.g., perform calculations, filtering, etc.)
            # For this example, we'll just print the first few rows of each chunk
            print(chunk.head())
    
    except FileNotFoundError:
        print(f"Error: The file at {csv_path} was not found.")
    except pd.errors.EmptyDataError:
        print(f"Error: The file at {csv_path} is empty.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
csv_path = 'sales_data.csv'
process_csv(csv_path)
