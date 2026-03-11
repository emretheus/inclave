## Reading CSV Files
```python
# Basic CSV read
df = pd.read_csv('file.csv')

# With encoding and delimiter
df = pd.read_csv('file.csv', encoding='utf-8', delimiter=';')

# Read specific columns only
df = pd.read_csv('file.csv', usecols=['name', 'age', 'salary'])

# Handle large files with chunking
for chunk in pd.read_csv('large_file.csv', chunksize=10000):
    process(chunk)

# Skip rows and set header
df = pd.read_csv('file.csv', skiprows=2, header=0)
```

## Handling Missing Values
```python
# Check for nulls
df.isnull().sum()

# Fill with mean (numeric columns)
df['column'] = df['column'].fillna(df['column'].mean())

# Fill with mode (categorical columns)
df['column'] = df['column'].fillna(df['column'].mode()[0])

# Fill with a specific value
df['discount'] = df['discount'].fillna(0)

# Drop rows with any null
df_clean = df.dropna()

# Drop rows where specific column is null
df_clean = df.dropna(subset=['important_column'])

# Forward fill (time series)
df['value'] = df['value'].fillna(method='ffill')
```

## Grouping and Aggregation
```python
# Group by single column
result = df.groupby('city')['revenue'].sum()

# Group by multiple columns with multiple aggregations
result = df.groupby(['city', 'product']).agg(
    total_revenue=('revenue', 'sum'),
    avg_quantity=('quantity', 'mean'),
    order_count=('revenue', 'count')
).reset_index()

# Pivot table
pivot = pd.pivot_table(df, values='revenue', index='city', columns='product', aggfunc='sum')

# Value counts
df['city'].value_counts()

# Crosstab
pd.crosstab(df['city'], df['product'])
```

## Filtering Data
```python
# Simple filter
df_filtered = df[df['revenue'] > 1000]

# Multiple conditions
df_filtered = df[(df['city'] == 'Istanbul') & (df['revenue'] > 1500)]

# Filter with isin
df_filtered = df[df['city'].isin(['Istanbul', 'Ankara'])]

# String contains
df_filtered = df[df['notes'].str.contains('order', na=False)]

# Filter by date range
df['date'] = pd.to_datetime(df['date'])
df_filtered = df[(df['date'] >= '2024-01-16') & (df['date'] <= '2024-01-20')]
```

## Sorting Data
```python
# Sort by single column
df_sorted = df.sort_values('revenue', ascending=False)

# Sort by multiple columns
df_sorted = df.sort_values(['city', 'revenue'], ascending=[True, False])

# Sort by index
df_sorted = df.sort_index()

# Get top N
top_5 = df.nlargest(5, 'revenue')
bottom_5 = df.nsmallest(5, 'revenue')
```

## Date and Time Operations
```python
# Convert string to datetime
df['date'] = pd.to_datetime(df['date'])

# Extract date components
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['day_name'] = df['date'].dt.day_name()

# Group by month
monthly = df.groupby(df['date'].dt.to_period('M'))['revenue'].sum()

# Date difference
df['days_since'] = (pd.Timestamp.now() - df['date']).dt.days

# Resample time series
daily = df.set_index('date').resample('D')['revenue'].sum()
```

## Merging and Joining
```python
# Merge two dataframes
merged = pd.merge(df1, df2, on='customer_id', how='left')

# Merge on different column names
merged = pd.merge(df1, df2, left_on='id', right_on='customer_id')

# Concatenate vertically
combined = pd.concat([df1, df2], ignore_index=True)

# Concatenate horizontally
combined = pd.concat([df1, df2], axis=1)
```

## Duplicate Handling
```python
# Find duplicates
duplicates = df[df.duplicated()]
duplicate_count = df.duplicated().sum()

# Find duplicates based on specific columns
duplicates = df[df.duplicated(subset=['customer_id', 'date'])]

# Remove duplicates
df_clean = df.drop_duplicates()

# Keep first/last occurrence
df_clean = df.drop_duplicates(subset=['customer_id'], keep='first')
```

## Data Type Conversion
```python
# Convert to numeric
df['price'] = pd.to_numeric(df['price'], errors='coerce')

# Convert to string
df['id'] = df['id'].astype(str)

# Convert to category (memory efficient)
df['city'] = df['city'].astype('category')

# Convert to datetime
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
```

## Statistical Analysis
```python
# Descriptive statistics
df.describe()
df.describe(include='all')

# Correlation matrix
corr = df.select_dtypes(include='number').corr()

# Value distribution
df['column'].describe()
df['column'].quantile([0.25, 0.5, 0.75])

# IQR outlier detection
Q1 = df['revenue'].quantile(0.25)
Q3 = df['revenue'].quantile(0.75)
IQR = Q3 - Q1
outliers = df[(df['revenue'] < Q1 - 1.5 * IQR) | (df['revenue'] > Q3 + 1.5 * IQR)]
```

## Visualization with Matplotlib
```python
import matplotlib.pyplot as plt

# Bar chart
df.groupby('city')['revenue'].sum().plot(kind='bar')
plt.title('Revenue by City')
plt.ylabel('Revenue')
plt.tight_layout()
plt.savefig('chart.png')
plt.show()

# Line chart
df.groupby('date')['revenue'].sum().plot(kind='line')
plt.title('Revenue Over Time')
plt.show()

# Histogram
df['revenue'].hist(bins=20)
plt.title('Revenue Distribution')
plt.xlabel('Revenue')
plt.show()

# Scatter plot
plt.scatter(df['quantity'], df['revenue'])
plt.xlabel('Quantity')
plt.ylabel('Revenue')
plt.title('Quantity vs Revenue')
plt.show()

# Heatmap (correlation matrix)
import numpy as np
corr = df.select_dtypes(include='number').corr()
fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(corr, cmap='coolwarm', aspect='auto')
ax.set_xticks(range(len(corr.columns)))
ax.set_yticks(range(len(corr.columns)))
ax.set_xticklabels(corr.columns, rotation=45, ha='right')
ax.set_yticklabels(corr.columns)
plt.colorbar(im)
plt.title('Correlation Matrix')
plt.tight_layout()
plt.show()

# Multiple subplots
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
df.groupby('city')['revenue'].sum().plot(kind='bar', ax=axes[0], title='Revenue by City')
df['revenue'].hist(bins=15, ax=axes[1])
axes[1].set_title('Revenue Distribution')
plt.tight_layout()
plt.show()
```

## Exporting Data
```python
# Export to CSV
df.to_csv('output.csv', index=False)

# Export to Excel
df.to_excel('output.xlsx', sheet_name='Sales', index=False)

# Export to JSON
df.to_json('output.json', orient='records', indent=2)

# Export specific columns
df[['city', 'revenue']].to_csv('summary.csv', index=False)
```

## Column Operations
```python
# Rename columns
df = df.rename(columns={'old_name': 'new_name'})

# Add calculated column
df['total'] = df['revenue'] * df['quantity']
df['revenue_per_unit'] = df['revenue'] / df['quantity']

# Apply function to column
df['city_upper'] = df['city'].apply(str.upper)
df['revenue_category'] = df['revenue'].apply(lambda x: 'High' if x > 2000 else 'Low')

# String operations
df['notes_clean'] = df['notes'].str.strip().str.lower()

# Binning
df['revenue_bin'] = pd.cut(df['revenue'], bins=[0, 1000, 2000, 5000], labels=['Low', 'Mid', 'High'])
```

## Data Preview and Info
```python
# First/last rows
df.head()
df.tail(10)

# Shape and info
print(f"Shape: {df.shape}")
df.info()
df.dtypes

# Memory usage
df.memory_usage(deep=True)

# Unique values
df['column'].unique()
df.nunique()
```
