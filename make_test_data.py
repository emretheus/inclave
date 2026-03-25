import pandas as pd
import numpy as np
import os

# 10 farklı satır + 1 birebir kopya satır = 11 satır
data = {
    "id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10], # 10. satır kopyalandı (Duplicate testi için)
    "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", 
             "2024-01-06", "2024-01-07", "2024-01-08", "2024-01-09", "2024-01-10", "2024-01-10"], # Datetime testi için
    "product": ["A", "B", "A", "C", "B", "A", "C", "A", "B", "C", "C"],
    "price": [10.0, 20.0, 10.0, 30.0, 20.0, 10.0, 30.0, 10.0, 20.0, 30.0, 30.0],
    "quantity": [1, 2, 1, 3, 2, 1, 3, 1, 2, 3, 3],
    "discount": [0.1, np.nan, 0.05, np.nan, 0.2, 0.1, np.nan, 0.0, 0.1, 0.15, 0.15], # Null (Boş) veri testi için
    "customer": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C10"],
    "location": ["L1", "L2", "L1", "L3", "L2", "L1", "L3", "L1", "L2", "L3", "L3"]
}

# 8 Sütunlu veri çerçevemizi oluşturup kaydediyoruz
df = pd.DataFrame(data)
os.makedirs("data/sample_csvs", exist_ok=True)
df.to_csv("data/sample_csvs/sales_data.csv", index=False)
print("Test verisi 'sales_data.csv' başarıyla oluşturuldu!")