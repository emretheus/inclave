from src.vectordb.store import VectorStore

store = VectorStore(collection_name="test")
store.reset()

# Add some pandas-related snippets
store.add_documents(
    doc_ids=["1", "2", "3"],
    texts=[
        "pd.read_csv('file.csv') reads a CSV file into a DataFrame",
        "df.groupby('column').mean() groups data and calculates averages",
        "df.to_excel('output.xlsx') exports DataFrame to Excel format",
    ],
    metadatas=[
        {"source": "pandas_docs", "topic": "io"},
        {"source": "pandas_docs", "topic": "groupby"},
        {"source": "pandas_docs", "topic": "io"},
    ],
)

print(f"Documents stored: {store.count()}")

results = store.search("how to read csv file in pandas", top_k=2)
for r in results:
    print(f"  Score: {r['score']:.3f} | {r['text'][:80]}")