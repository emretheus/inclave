# test_schema_manual.py
from typing import Optional
from src.csv_engine.schema_analyzer import SchemaAnalyzer

analyzer = SchemaAnalyzer()
schema = analyzer.analyze("data/sample_csvs/sales_data.csv")

print(schema.to_prompt_string())
print("\n--- Raw Issues ---")
for issue in schema.potential_issues:
    print(f"  - {issue}")