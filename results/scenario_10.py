import pandas as pd

# Function to clean the CSV file by removing duplicate rows
def clean_csv(csv_path):
    try:
        # Read the CSV file in chunks to handle large files
        chunksize = 10000
        for chunk in pd.read_csv(csv_path, chunksize=chunksize):
            # Remove duplicate rows within each chunk
            chunk_clean = chunk.drop_duplicates()
            # Append the cleaned chunk back to a new DataFrame
            if 'df_clean' not in locals():
                df_clean = chunk_clean
            else:
                df_clean = pd.concat([df_clean, chunk_clean], ignore_index=True)
        
        # Save the cleaned data to a new CSV file
        df_clean.to_csv('cleaned_sales_data.csv', index=False)
        print("Duplicate rows removed and cleaned data saved as 'cleaned_sales_data.csv'")
    
    except FileNotFoundError:
        print(f"Error: The file at {csv_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
csv_path = 'sales_data.csv'
clean_csv(csv_path)
