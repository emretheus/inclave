from src.rag.retriever import KnowledgeRetriever

# Arama motorunu başlat
retriever = KnowledgeRetriever()

# Yapay zekadan isteyeceğimiz sahte bir görev (sorgu) belirliyoruz
gorev = "Şehir (city) bazında toplam gelirleri (revenue) hesapla."

# CSV şemasından elde ettiğimiz sahte bir ipucu veriyoruz
ipucu = "columns: city(object), revenue(float64)"

print(f"Sorgu: '{gorev}'")
print(f"Şema İpucu: '{ipucu}'")
print("Veritabanında aranıyor...\n")

# Arama işlemini yap
context = retriever.retrieve(query=gorev, schema_hint=ipucu)

if context:
    print("--- BULUNAN KOPYA KAĞITLARI (CONTEXT) ---")
    print(context)
else:
    print("Maalesef, veritabanında bu konuyla ilgili yeterince benzer bir bilgi bulunamadı.")