from src.llm.pipeline import CodePipeline

pipeline = CodePipeline()

result = pipeline.generate(
    csv_path="data/sample_csvs/sales_data.csv",
    user_prompt="Read the CSV and show basic statistics for all numeric columns"
)

print("=== Generated Code ===")
print(result.code)
print("\n=== Schema Used ===")
print(result.csv_schema)
print(f"\n=== RAG Context Length: {len(result.rag_context)} chars ===")