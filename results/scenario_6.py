import pandas as pd

# Function to merge CSV files by customer_id
def merge_csv_files(csv_path):
    try:
        # Read the main sales data CSV
        df_sales = pd.read_csv(csv_path)
        
        # Convert 'date' column to datetime if necessary
        df_sales['date'] = pd.to_datetime(df_sales['date'])
        
        # Read the employees CSV file
        df_employees = pd.read_csv('data/sample_csvs/employees.csv')
        
        # Merge the two DataFrames on 'customer_id'
        merged_df = pd.merge(df_sales, df_employees, on='customer_id', how='left')
        
        # Return the merged DataFrame
        return merged_df
    
    except FileNotFoundError:
        print("File not found. Please check the file path.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
csv_path = 'sales_data.csv'
merged_result = merge_csv_files(csv_path)
print(merged_result)
