from src.llm.classifier import QueryClassifier, QueryCategory

classifier = QueryClassifier()

test_cases = [
    ("show first 5 rows", QueryCategory.SIMPLE),
    ("bar chart of revenue by city", QueryCategory.VISUALIZATION),
    ("fill missing values with mean", QueryCategory.CLEANING),
    ("total revenue by city and product", QueryCategory.AGGREGATION),
    ("count rows", QueryCategory.SIMPLE),
    ("histogram of age distribution", QueryCategory.VISUALIZATION),
    ("remove duplicate entries", QueryCategory.CLEANING),
    ("pivot table by department and quarter", QueryCategory.AGGREGATION),
    ("merge with employees, clean nulls, then plot top 10", QueryCategory.COMPLEX),
]

correct = 0
for query, expected in test_cases:
    result = classifier.classify(query)
    match = "✅" if result.category == expected else "❌"
    if result.category == expected:
        correct += 1
    print(f"{match} '{query}'")
    print(f"   → got: {result.category.value} | expected: {expected.value} | confidence: {result.confidence:.2f} | method: {result.method}")

print(f"\nAccuracy: {correct}/{len(test_cases)} ({correct/len(test_cases)*100:.0f}%)")