import pandas as pd
import matplotlib.pyplot as plt

# Function to plot monthly temperature trend from a CSV file
def plot_monthly_temperature_trend(csv_path):
    try:
        # Read the CSV file in chunks if it's large
        chunk_size = 1000
        date_parser = lambda x: pd.to_datetime(x, format='%Y-%m-%d')
        
        temperature_data = []
        for chunk in pd.read_csv(csv_path, usecols=['date', 'temperature'], parse_dates=['date'], chunksize=chunk_size):
            # Convert string column to datetime if necessary
            chunk['date'] = pd.to_datetime(chunk['date'])
            
            # Extract year and month
            chunk['year_month'] = chunk['date'].dt.to_period('M')
            
            # Group by year-month and calculate mean temperature
            monthly_avg_temp = chunk.groupby('year_month')['temperature'].mean().reset_index()
            temperature_data.append(monthly_avg_temp)
        
        # Concatenate all chunks if necessary
        if len(temperature_data) > 1:
            df = pd.concat(temperature_data, ignore_index=True)
        else:
            df = temperature_data[0]
        
        # Plot the monthly temperature trend
        plt.figure(figsize=(10, 6))
        plt.plot(df['year_month'], df['temperature'], marker='o', linestyle='-')
        plt.title('Monthly Temperature Trend')
        plt.xlabel('Month')
        plt.ylabel('Average Temperature')
        plt.grid(True)
        plt.show()
    
    except FileNotFoundError:
        print(f"File not found: {csv_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
csv_path = 'weather.csv'
plot_monthly_temperature_trend(csv_path)
