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

## Handling Missing Values

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

## Grouping and Aggregation

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



