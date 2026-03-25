import streamlit as st
import pandas as pd
import tempfile
import os
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer
import subprocess
import time
import urllib.request

# Sayfa ayarlarını yapıyoruz (Geniş ekran modu ve sekme başlığı)
st.set_page_config(page_title="Enclave CodeRunner", page_icon="🤖", layout="wide")

# Streamlit ekrandaki her butona basıldığında kodu baştan aşağı tekrar okur.
# Sürekli Ollama ve ChromaDB'ye baştan bağlanmamak için @st.cache_resource kullanıyoruz.
@st.cache_resource
def load_system():
    return CodePipeline(), KnowledgeIndexer()

pipeline, indexer = load_system()

# --- 1. SOL YAN PANEL (SIDEBAR) ---
with st.sidebar:
    st.title("⚙️ Sistem Durumu")

    # YENİ: DİNAMİK OLLAMA KONTROLÜ
    def is_ollama_running():
        """Ollama'nın 11434 portuna ping atarak çalışıp çalışmadığını kontrol eder."""
        try:
            # 1 saniye içinde cevap verirse ayaktadır
            urllib.request.urlopen("http://127.0.0.1:11434/", timeout=1)
            return True
        except Exception:
            return False

    ollama_active = is_ollama_running()
    
    # Duruma göre dinamik rozet (Badge)
    if ollama_active:
        st.success("🟢 Ollama: Bağlı ve Çalışıyor")
    else:
        st.error("🔴 Ollama: Ulaşılamıyor (Kapalı)")
    
    # RAG ve Hafıza istatistiklerini çekiyoruz
    stats = indexer.get_stats()
    few_shot_count = pipeline.few_shot.count() if hasattr(pipeline, 'few_shot') else 0
    
    st.metric(label="📚 RAG Bilgi Parçaları", value=stats["total_chunks"])
    st.metric(label="🧠 Hafızadaki Başarılı Kodlar", value=few_shot_count)
    st.markdown("---")

    # YENİ: OLLAMA KONTROL PANELİ
    st.subheader("🦙 Ollama Kontrolü")

    def start_ollama():
        try:
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception:
            return False

    # Sadece Ollama kapalıysa başlatma butonunu göster! (Mükemmel UX)
    # Sadece Ollama kapalıysa başlatma butonunu göster!
    if not ollama_active:
        if st.button("🔌 Ollama'yı Başlat", use_container_width=True):
            with st.spinner("Servis başlatılıyor..."):
                if start_ollama():
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Başlatılamadı!")
    else:
        st.info("Ollama şu an hizmet vermeye hazır.")
        # YENİ: OLLAMA AÇIKKEN GÖRÜNECEK "KAPAT" BUTONU
        if st.button("🛑 Ollama'yı Kapat", use_container_width=True):
            with st.spinner("Ollama kapatılıyor..."):
                try:
                    # Windows'ta arkaplandaki Ollama'yı zorla (Force) kapatma komutu
                    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    time.sleep(1) # Sistemin kapanması için 1 saniye bekle
                    st.rerun() # Arayüzü yenile (kırmızı ışık yansın)
                except Exception as e:
                    st.error("Kapatılırken hata oluştu!")
        
    st.caption("Geliştirici: Enclave Ekibi")

# --- 2. ANA EKRAN (MAIN AREA) ---
st.title("🤖 Enclave AI: Otonom Veri Analisti")
st.markdown("CSV dosyanızı yükleyin ve ne yapmak istediğinizi İngilizce olarak söyleyin. Gerisini yapay zekaya bırakın!")

# Dosya yükleme aracı (Sadece CSV kabul eder)
uploaded_file = st.file_uploader("Bir CSV Dosyası Yükleyin", type=["csv"])

if uploaded_file is not None:
    # Dosya yüklendiğinde, arka planda (temp) bir yere kaydedelim ki Pipeline okuyabilsin
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        # Önizleme için veriyi pandas ile okuyup arayüze basalım
        df_preview = pd.read_csv(tmp_path)
        
        # --- METRİK KARTLARI (Satır, Sütun Sayısı vb.) ---
        col1, col2, col3 = st.columns(3) # Ekranı 3 kolona böl
        col1.metric("Toplam Satır", df_preview.shape[0])
        col2.metric("Toplam Sütun", df_preview.shape[1])
        col3.metric("Boş Hücre (Null) Sayısı", df_preview.isnull().sum().sum())

        st.markdown("### 📊 Veri Önizleme (İlk 5 Satır)")
        st.dataframe(df_preview.head()) # Veriyi harika bir interaktif tablo olarak çizer

        # --- YAPAY ZEKA SOHBET VE KOD ÜRETİM ALANI ---
        st.markdown("---")
        st.subheader("💡 Yapay Zekaya Görev Ver")
        
        # 1. HAZIR PROMPTLARI TANIMLA
        TITANIC_PROMPTS = {
            "🚢 Survival by Gender": "Calculate survival rate by Sex, show bar chart",
            "💰 Class & Fare": "Average Fare by Pclass, bar chart with passenger count",
            "👶 Age Distribution": "Histogram of Age for survived vs died, handle NaN",
            "👨‍👩‍👧 Family Effect": "Create family_size from SibSp+Parch, survival rate by family size",
            "🚪 Embarkation Analysis": "Survival rate and avg fare by Embarked, dual-axis chart",
            "📊 Summary Pivot": "Pivot table: Pclass x Sex with survival rate, avg age, avg fare",
        }

        GENERIC_PROMPTS = {
            "📊 Basic Stats": "Show descriptive statistics for all numeric columns",
            "🔍 Null Analysis": "Show null counts and percentages, suggest how to handle them",
            "📈 Distribution": "Plot histogram for each numeric column",
            "🔗 Correlation": "Show correlation matrix heatmap for numeric columns",
            "📋 Top Values": "Show value counts for each categorical column",
        }

        # Dosya adına göre hangi listeyi göstereceğimizi seç (Büyük/küçük harf duyarsız)
        is_titanic = "titanic" in uploaded_file.name.lower()
        active_prompts = TITANIC_PROMPTS if is_titanic else GENERIC_PROMPTS

        # 2. BUTONLARA TIKLANINCA METİN KUTUSUNU DOLDURACAK FONKSİYON
        if "current_prompt" not in st.session_state:
            st.session_state.current_prompt = ""

        def set_prompt(text):
            st.session_state.current_prompt = text

        # 3. BUTONLARI YAN YANA DİZ
        st.caption("Örnek Hazır Görevler (Tıklayarak seçebilirsiniz):")
        # Butonları 3'lü kolonlar halinde dizmek için:
        cols = st.columns(3)
        for i, (label, prompt_text) in enumerate(active_prompts.items()):
            # on_click metodu ile butona basılınca set_prompt fonksiyonunu tetikliyoruz
            cols[i % 3].button(label, on_click=set_prompt, args=(prompt_text,), use_container_width=True)

        # 4. KULLANICI METİN KUTUSU
        user_prompt = st.text_area(
            "Bu veri setiyle ne yapmak istiyorsun?", 
            value=st.session_state.current_prompt, # Değer state'den gelir
            height=100
        )
        
              
        # Butona basıldığında çalışacak kodlar
        if st.button("🚀 Kodu Üret ve Çalıştır", type="primary"):
            if not user_prompt.strip():
                st.warning("Lütfen önce bir görev yazın!")
            else:
                with st.spinner("Yapay Zeka düşünüyor, kod yazıyor ve test ediyor... Lütfen bekleyin."):
                    # Sistemimizin kalbini çağırıyoruz!
                    result = pipeline.generate(csv_path=tmp_path, user_prompt=user_prompt)
                    
                    # Sonuçları göstermek için Sekmeler (Tabs) oluşturuyoruz
                    tab1, tab2, tab3 = st.tabs(["💻 Üretilen Kod", "📊 Terminal Çıktısı", "⚙️ Şema ve Analiz Detayı"])
                    
                    with tab1:
                        if result.execution_success:
                            st.success(f"✅ Kod başarıyla çalıştı! (Kendi kendini iyileştirme {result.attempts}/3 denemede bitti)")
                        else:
                            st.error(f"❌ Kod {result.attempts} denemeye rağmen çalıştırılamadı!")
                        
                        st.code(result.code, language="python") # Kodu renkli syntax ile gösterir
                    
                    with tab2:
                        if result.execution_success:
                            # Çıktı boşsa uyar, doluysa terminal ekranı gibi göster
                            output_text = result.execution_output if result.execution_output.strip() else "(Kod başarıyla çalıştı ancak ekrana bir şey yazdırmadı - print() kullanılmamış olabilir)"
                            st.text(output_text)

                            if os.path.exists("output.png"):
                                st.markdown("### 📈 Çizilen Grafik:")
                                st.image("output.png")
                                os.remove("output.png") # Bir sonraki test için ortalığı temizle

                        else:
                            st.error("Alınan Son Hata:")
                            st.code(result.execution_error, language="bash")
                            
                    with tab3:
                        st.text(result.csv_schema)
                        st.write(f"**RAG Kullanıldı mı?** {'Evet' if result.rag_context else 'Hayır'}")

    finally:
        # İşlem bitince geçici dosyayı temizle
        if os.path.exists(tmp_path):
            os.remove(tmp_path)