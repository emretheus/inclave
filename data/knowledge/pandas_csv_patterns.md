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
```

## Handling Missing Values
```python
# Check for nulls
df.isnull().sum()

# Fill with mean (numeric columns)
df['column'] = df['column'].fillna(df['column'].mean())

# Fill with mode (categorical columns)
df['column'] = df['column'].fillna(df['column'].mode()[0])

# Drop rows with any null
df_clean = df.dropna()

# Drop rows where specific column is null
df_clean = df.dropna(subset=['important_column'])
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
```

## Datetime Operations
```python
# Convert string column to datetime
df['date'] = pd.to_datetime(df['date'])

# Extract year, month, day
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month

# Filter by date range
mask = (df['date'] >= '2024-01-01') & (df['date'] <= '2024-12-31')
df_filtered = df[mask]

# Sort by date
df_sorted = df.sort_values('date')
```

## Filtering and Selecting Data
```python
# Filter rows by condition
df_filtered = df[df['revenue'] > 1000]

# Filter by multiple conditions
df_filtered = df[(df['city'] == 'Istanbul') & (df['revenue'] > 1000)]

# Select specific columns
df_small = df[['name', 'revenue', 'city']]

# Filter by list of values
df_filtered = df[df['city'].isin(['Istanbul', 'Ankara'])]
```

## Removing Duplicates
```python
# Find duplicate rows
duplicates = df[df.duplicated()]

# Count duplicates
print(df.duplicated().sum())

# Remove duplicate rows
df_clean = df.drop_duplicates()

# Remove duplicates based on specific columns
df_clean = df.drop_duplicates(subset=['customer_id', 'date'])
```

## Sorting Data
```python
# Sort by single column ascending
df_sorted = df.sort_values('revenue')

# Sort by single column descending
df_sorted = df.sort_values('revenue', ascending=False)

# Sort by multiple columns
df_sorted = df.sort_values(['city', 'revenue'], ascending=[True, False])
```

## Renaming and Dropping Columns
```python
# Rename columns
df = df.rename(columns={'old_name': 'new_name', 'revenue': 'total_revenue'})

# Drop a column
df = df.drop(columns=['notes'])

# Drop multiple columns
df = df.drop(columns=['notes', 'customer_id'])
```

## Basic Statistics
```python
# Summary statistics for all numeric columns
df.describe()

# Summary statistics for specific column
df['revenue'].describe()

# Correlation matrix
df.corr()

# Value counts for categorical column
df['city'].value_counts()
```

## Exporting Data
```python
# Export to CSV
df.to_csv('output.csv', index=False)

# Export to Excel with sheet name
df.to_excel('output.xlsx', sheet_name='Sales', index=False)

# Export specific columns to CSV
df[['city', 'revenue']].to_csv('summary.csv', index=False)
```