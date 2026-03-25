# test_vectordb_manual.py
from src.vectordb.store import VectorStore

# 'test' adında geçici bir koleksiyon açıyoruz
store = VectorStore(collection_name="test")

# İçini temizliyoruz (eski testlerden kalanlar olmasın diye)
store.reset()

print("Dökümanlar vektörleştiriliyor ve veritabanına ekleniyor...")

# Pandas ile ilgili birkaç bilgi kırıntısı (snippet) ekliyoruz
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

print(f"Veritabanına eklenen döküman sayısı: {store.count()}\n")

# Anlamsal arama (Semantic Search) yapıyoruz
arama_metni = "how to read csv file in pandas"
print(f"Sorgu: '{arama_metni}'")
print("-" * 50)

results = store.search(arama_metni, top_k=2)

for r in results:
    print(f"Skor: {r['score']:.3f} | Metin: {r['text']}")