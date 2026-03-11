import pandas as pd

def merge_files(csv_path):
    try:
        # Read the main sales data CSV
        df_sales = pd.read_csv(csv_path)
        
        # Convert 'date' column to datetime
        df_sales['date'] = pd.to_datetime(df_sales['date'])
        
        # Read the employees CSV
        df_employees = pd.read_csv('data/sample_csvs/employees.csv')
        
        # Merge the two DataFrames on 'customer_id'
        merged_df = pd.merge(df_sales, df_employees, on='customer_id', how='left')
        
        # Drop rows with null values in 'notes' column
        merged_df.dropna(subset=['notes'], inplace=True)
        
        # Export the merged DataFrame to a new CSV file
        merged_df.to_csv('merged_data.csv', index=False)
        
        print("Files merged successfully and saved as 'merged_data.csv'")
    
    except FileNotFoundError:
        print(f"File not found. Please check the path: {csv_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
merge_files('sales_data.csv')
