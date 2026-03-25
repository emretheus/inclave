from src.llm.classifier import QueryClassifier, QueryCategory

print("Sınıflandırıcı (Query Classifier) test ediliyor...\n")
classifier = QueryClassifier()

test_cases = [
    ("show first 5 rows", QueryCategory.SIMPLE),
    ("bar chart of revenue by city", QueryCategory.VISUALIZATION),
    ("fill missing values with mean", QueryCategory.CLEANING),
    ("total revenue by city and product", QueryCategory.AGGREGATION),
    ("merge with employees, clean nulls, then plot top 10 by salary", QueryCategory.COMPLEX),
    ("count rows", QueryCategory.SIMPLE),
    ("histogram of age distribution", QueryCategory.VISUALIZATION),
    ("remove duplicate entries", QueryCategory.CLEANING),
    ("pivot table by department and quarter", QueryCategory.AGGREGATION),
]

correct = 0
for query, expected in test_cases:
    # Sınıflandırıcıyı çalıştır
    result = classifier.classify(query)
    
    # Eşleşmeyi kontrol et
    match = "✅" if result.category == expected else "❌"
    if result.category == expected:
        correct += 1
        
    print(f"{match} '{query}'")
    print(f"    ↳ Bulunan: {result.category.value.upper()} (Beklenen: {expected.value.upper()})")
    print(f"    ↳ Yöntem: {result.method.upper()} | Güven Skoru: {result.confidence:.2f}\n")

accuracy = correct / len(test_cases) * 100
print(f"🎯 Başarı Oranı (Accuracy): {correct}/{len(test_cases)} ({accuracy:.0f}%)")