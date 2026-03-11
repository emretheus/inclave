import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the CSV file
try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print("File not found. Please check the path and try again.")
    exit()
except Exception as e:
    print(f"An error occurred: {e}")
    exit()

# Convert 'hire_date' to datetime if necessary
if df['hire_date'].dtype == 'object':
    df['hire_date'] = pd.to_datetime(df['hire_date'])

# Create a correlation matrix
correlation_matrix = df.corr()

# Plotting the heatmap
plt.figure(figsize=(10, 8))
plt.title('Correlation Matrix Heatmap')
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', linewidths=0.5)
plt.show()
