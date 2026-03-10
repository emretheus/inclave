from src.rag.indexer import KnowledgeIndexer
from src.rag.retriever import KnowledgeRetriever

# Step 1: Index
indexer = KnowledgeIndexer()
indexer.index_knowledge_dir(force_reindex=True)
print(indexer.get_stats())

# Step 2: Retrieve
retriever = KnowledgeRetriever()

# Test queries
test_queries = [
    "how to read a CSV file",
    "fill missing values in dataframe",
    "group by column and sum",
    "export to excel",
    "find duplicate rows",
]

for q in test_queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    context = retriever.retrieve(q, top_k=2)
    if context:
        print(f"Context (first 200 chars): {context[:200]}...")
    else:
        print("No relevant context found")