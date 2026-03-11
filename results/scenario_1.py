import pandas as pd

# Read the CSV file using the provided csv_path variable
try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print("File not found. Please check the file path.")
    exit()
except Exception as e:
    print(f"An error occurred: {e}")
    exit()

# Convert 'date' column to datetime format
df['date'] = pd.to_datetime(df['date'])

# Display the first 5 rows of the DataFrame
print(df.head(5))