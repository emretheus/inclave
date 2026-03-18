from src.cache.semantic_cache import SemanticCache

cache = SemanticCache()

# Store a result
cache.store_result(
    query="Show total revenue by city",
    schema_fingerprint="abc123",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('city')['revenue'].sum())",
    execution_output="Istanbul  8600.50\nAnkara   5150.00\n...",
)

print("✅ Stored result successfully")

# Test 1: exact match
hit = cache.lookup("Show total revenue by city", "abc123")
assert hit is not None
print(f"✅ Exact match found: {hit.code[:50]}...")

# Test 2: semantic similarity
hit = cache.lookup("Display sum of revenue per city", "abc123")
if hit:
    print(f"✅ Semantic match found: {hit.code[:50]}...")
else:
    print("⚠️  Semantic match not found — threshold may be too high")

# Test 3: different schema — should miss
miss = cache.lookup("Show total revenue by city", "xyz789")
assert miss is None
print("✅ Different schema: cache miss (correct)")

# Stats
print(f"\nCache stats: {cache.stats()}")