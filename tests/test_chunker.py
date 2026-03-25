from src.rag.chunking import MarkdownCodeChunker

chunker = MarkdownCodeChunker()
dosya_yolu = "data/knowledge/pandas_csv_patterns.md"

# Parçalama işlemini yap
chunks = chunker.chunk_file(dosya_yolu)

print(f"Toplam {len(chunks)} parça (chunk) bulundu!\n")

for c in chunks:
    print(f"ID: {c.id}")
    print(f"Başlık: {c.metadata['title']}")
    print(f"Karakter Sayısı: {len(c.text)}")
    print("-" * 30)