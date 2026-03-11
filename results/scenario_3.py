import pandas as pd

# Function to convert date column to datetime and save the modified DataFrame to a new CSV file
def convert_date_column(csv_path):
    try:
        # Read the CSV file in chunks to handle large files
        chunksize = 10000
        for chunk in pd.read_csv(csv_path, chunksize=chunksize):
            # Convert the 'date' column to datetime
            chunk['date'] = pd.to_datetime(chunk['date'])
            
            # Save the modified chunk to a new CSV file
            chunk.to_csv('modified_sales_data.csv', mode='a', header=False, index=False)
    
    except FileNotFoundError:
        print(f"Error: The file at {csv_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
csv_path = 'sales_data.csv'
convert_date_column(csv_path)
