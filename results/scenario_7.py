import pandas as pd
import numpy as np

def find_outliers(csv_path):
    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Convert 'date' column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter out rows with null values in 'temperature'
        df_filtered = df.dropna(subset=['temperature'])
        
        # Calculate Q1 and Q3 for the 'temperature' column
        Q1 = df_filtered['temperature'].quantile(0.25)
        Q3 = df_filtered['temperature'].quantile(0.75)
        
        # Calculate IQR
        IQR = Q3 - Q1
        
        # Define the lower and upper bounds for outliers
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Identify outliers
        outliers = df_filtered[(df_filtered['temperature'] < lower_bound) | (df_filtered['temperature'] > upper_bound)]
        
        return outliers
    
    except FileNotFoundError:
        print(f"File not found: {csv_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
outliers = find_outliers('weather.csv')
print(outliers)
