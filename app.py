import streamlit as st
import pandas as pd
import tempfile
import os
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer
import subprocess
import time
import urllib.request
import uuid
from src.config import PIPELINE_MODE
import glob


# Sayfa ayarlarını yapıyoruz (Geniş ekran modu ve sekme başlığı)
st.set_page_config(page_title="Enclave CodeRunner", page_icon="🤖", layout="wide")

# Streamlit ekrandaki her butona basıldığında kodu baştan aşağı tekrar okur.
# Sürekli Ollama ve ChromaDB'ye baştan bağlanmamak için @st.cache_resource kullanıyoruz.
@st.cache_resource
def load_system():
    return CodePipeline(), KnowledgeIndexer()

pipeline, indexer = load_system()

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "type": "text",
            "content": "👋 Merhaba! Veri setinle ilgili bana dilediğini sorabilirsin. Sorgularını anımsayabilirim."
        }
    ]

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

    #  OLLAMA KONTROL PANELİ
    st.subheader("🦙 Ollama Kontrolü")

    def start_ollama():
        try:
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception:
            return False

   
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
        # OLLAMA AÇIKKEN GÖRÜNECEK "KAPAT" BUTONU
        if st.button("🛑 Ollama'yı Kapat", use_container_width=True):
            with st.spinner("Ollama kapatılıyor..."):
                try:
                    # Windows'ta arkaplandaki Ollama'yı zorla (Force) kapatma komutu
                    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    time.sleep(3) # Sistemin kapanması için 1 saniye bekle
                    st.rerun() # Arayüzü yenile (kırmızı ışık yansın)
                except Exception as e:
                    st.error("Kapatılırken hata oluştu!")

    st.markdown("---")
    st.markdown(f"**🌐 Çalışma Modu:** `{PIPELINE_MODE.upper()}`")

    st.markdown("---")
    st.subheader("⚙️ Oturum ve Mod Ayarları")
    
    # 1. CLOUD MOD GEÇİŞİ (TOGGLE)
    import src.config
    initial_cloud_state = (src.config.PIPELINE_MODE == "cloud")
    
    use_cloud = st.toggle("☁️ Bulut Hakemi (Cloud Judge)", value=initial_cloud_state)
    
    # Toggle durumuna göre anında Pipeline'ı güncelle
    if use_cloud:
        src.config.PIPELINE_MODE = "cloud"
        # Eğer sistem Local başladıysa Cloud Judge objesi boştur, onu anında yükle:
        if getattr(pipeline, "cloud_judge", None) is None:
            from src.judge.judge_agent import CloudJudgeAgent
            pipeline.cloud_judge = CloudJudgeAgent()
    else:
        src.config.PIPELINE_MODE = "local"

    # 2. SOHBET/OTURUM SIFIRLAMA BUTONU
    if st.button("🗑️ Sohbeti Temizle (Yeni Oturum)", use_container_width=True):
        import uuid
        # Yeni tertemiz bir session id üret
        st.session_state["session_id"] = str(uuid.uuid4())
        # Ekrandaki metin kutusunu temizle
        if "current_prompt" in st.session_state:
            st.session_state["current_prompt"] = ""
        # Sayfayı yenile ki geçmiş sekmedeki konuşmalar hafızadan kopsun
        st.rerun()

   
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
        # tmp_path = tmp_file.name.replace("\\", "/")

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

        if len(st.session_state["messages"]) > 1:
            st.markdown("### 💬 Önceki Sorgular ve Sonuçlar")
            for msg in st.session_state["messages"][1:]: # İlk 'merhaba' mesajını atla
                with st.chat_message(msg["role"]):
                    if msg.get("type") == "text":
                        st.markdown(msg["content"])
                        
                    elif msg.get("type") == "result":
                        st.markdown(msg["content"])
                        
                        with st.expander("🔍 Detayları ve 4 Sekmeli Raporu İncele", expanded=False):
                            htab1, htab2, htab3, htab4 = st.tabs(["💻 Üretilen Kod", "📊 Terminal Çıktısı", "⚙️ Şema ve Analiz", "🤖 Ajan Raporları"])
                            
                            with htab1:
                                if msg.get("execution_success"):
                                    st.success(f"✅ Kod başarıyla çalıştı! (Kendi kendini iyileştirme {msg.get('attempts', 1)}/3 denemede bitti)")
                                else:
                                    st.error(f"❌ Kod {msg.get('attempts', 1)} denemeye rağmen çalıştırılamadı!")
                                if msg.get("code"):
                                    st.code(msg["code"], language="python")
                                    
                            with htab2:
                                if msg.get("execution_success"):
                                    output_text = msg.get("output", "")
                                    st.text(output_text if output_text.strip() else "(Kod başarıyla çalıştı ancak ekrana bir şey yazdırmadı - print() kullanılmamış olabilir)")
                                    # Not: Geçmiş grafikler silindiği için burada çıkmaz, terminal çıktısı gelir.
                                else:
                                    st.error("Alınan Son Hata:")
                                    if msg.get("error"):
                                        st.code(msg["error"], language="bash")
                                        
                            with htab3:
                                if msg.get("csv_schema"):
                                    st.text(msg.get("csv_schema"))
                                st.write(f"**Sorgu Kategorisi:** `{msg.get('query_category', 'Bilinmiyor').upper()}`")
                                st.write(f"**RAG Kullanıldı mı?** {'Evet' if msg.get('rag_context') else 'Hayır'}")
                                
                            with htab4:
                                col_rev, col_judge = st.columns(2)
                                with col_rev:
                                    st.markdown("#### 🕵️ Local Reviewer")
                                    rev_issues = msg.get("reviewer_issues", [])
                                    rev_fixed = msg.get("reviewer_fixed", False)
                                    if rev_issues or rev_fixed:
                                        if rev_fixed:
                                            st.success("İnceleyici ajan mantıksal hataları buldu ve kodu yeniden yazarak düzeltti!")
                                        for issue in rev_issues:
                                            st.warning(f"- {issue}")
                                    else:
                                        st.info("İnceleyici ajan kodda düzeltilecek bir mantıksal sorun bulmadı.")
                                        
                                with col_judge:
                                    st.markdown("#### ☁️ Cloud Judge")
                                    j_score = msg.get("judge_score")
                                    if j_score is not None:
                                        if msg.get("judge_passed"):
                                            st.success(f"✅ Hakem Onayladı (Puan: {j_score}/10.0)")
                                        else:
                                            st.error(f"❌ Hakem Reddetti (Puan: {j_score}/10.0)")
                                        
                                        st.markdown(f"**Geri Bildirim:** {msg.get('judge_feedback', '')}")
                                        det = msg.get("judge_details", {})
                                        if det:
                                            st.caption(f"Doğruluk: {det.get('correctness')}/10 | Niyet: {det.get('intent')}/10 | Kalite: {det.get('quality')}/10")
                                    else:
                                        st.info("Bulut Hakemi bu sorguda çalıştırılmadı (Basit sorgu veya Local Mod).")
        st.markdown("---")

        # 4. KULLANICI METİN KUTUSU
        user_prompt = st.text_area(
            "Bu veri setiyle ne yapmak istiyorsun?", 
            value=st.session_state.current_prompt, # Değer state'den gelir
            height=100
        )
        
              
        # Butona basıldığında çalışacak kodlar
        col_run, col_del = st.columns([4, 1])
        
        with col_run:
            # Mevcut st.button yerine bunu değişkene atıyoruz
            run_btn = st.button("🚀 Kodu Üret ve Çalıştır", type="primary", use_container_width=True)
            
        with col_del:
            # YENİ: SEÇİCİ UNUTMA BUTONU
            del_btn = st.button("🗑️ Yanlış Sonucu Unut", use_container_width=True)
              
        # --- Hafızadan Silme İşlemi ---
        if del_btn:
            if not user_prompt.strip():
                st.warning("Lütfen silmek istediğiniz sorguyu metin kutusuna yazın veya yukarıdan seçin.")
            else:
                # Pipeline üzerinden her iki hafızadan da siliyoruz
                pipeline.forget_query(tmp_path, user_prompt)
                st.success(f"✅ '{user_prompt}' sorgusu hafızalardan tamamen silindi! Şimdi tekrar çalıştırabilirsiniz.")

        # --- Üretim İşlemi ---
        if run_btn:
            if not user_prompt.strip():
                st.warning("Lütfen önce bir görev yazın!")
            else:
                with st.spinner("Yapay Zeka düşünüyor, kod yazıyor ve test ediyor... Lütfen bekleyin."):
                    
                    # 1. Sistemimizin kalbini çağırıyoruz (session_id eklenmiş haliyle!)
                    result = pipeline.generate(
                        csv_path=tmp_path, 
                        user_prompt=user_prompt,
                        session_id=st.session_state.get("session_id")
                    )
                    
                    # 2. Önbellek Uyarısı (Eğer çok hızlı geldiyse)
                    if getattr(result, "from_cache", False):
                        st.info("⚡ **Süper Hızlı Yanıt:** Bu sonuç Semantic Cache (Önbellek) kullanılarak saniyeler içinde getirildi!")
                    
                    # 3. Sonuçları göstermek için Sekmeler (YENİ: 4. Sekme eklendi)
                    tab1, tab2, tab3, tab4 = st.tabs(["💻 Üretilen Kod", "📊 Terminal Çıktısı", "⚙️ Şema ve Analiz", "🤖 Ajan Raporları"])
                    
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

                            import glob
                            # YENİ: Sadece 'output.png' değil, üretilen tüm grafikleri yakala
                            for plot_file in glob.glob("*.png"):
                                st.markdown(f"### 📈 Çizilen Grafik:")
                                st.image(plot_file)
                                os.remove(plot_file) # Temizle

                        else:
                            st.error("Alınan Son Hata:")
                            st.code(result.execution_error, language="bash")
                            
                    with tab3:
                        st.text(result.csv_schema)
                        st.write(f"**Sorgu Kategorisi:** `{getattr(result, 'query_category', 'Bilinmiyor').upper()}`")
                        st.write(f"**RAG Kullanıldı mı?** {'Evet' if result.rag_context else 'Hayır'}")
                        
                    with tab4:
                        #: AJAN RAPORLARI EKRANI
                        st.markdown("Bu ekranda bağımsız yapay zeka ajanlarının koda yaptığı yorumları görebilirsiniz.")
                        col_rev, col_judge = st.columns(2)
                        
                        with col_rev:
                            st.markdown("#### 🕵️ Local Reviewer")
                            if getattr(result, "reviewer_issues", None) or getattr(result, "reviewer_fixed", False):
                                if result.reviewer_fixed:
                                    st.success("İnceleyici ajan mantıksal hataları buldu ve kodu yeniden yazarak düzeltti!")
                                for issue in result.reviewer_issues:
                                    st.warning(f"- {issue}")
                            else:
                                st.info("İnceleyici ajan kodda düzeltilecek bir mantıksal sorun bulmadı.")
                                
                        with col_judge:
                            st.markdown("#### ☁️ Cloud Judge")
                            if getattr(result, "judge_score", None) is not None:
                                if result.judge_passed:
                                    st.success(f"✅ Hakem Onayladı (Puan: {result.judge_score}/10.0)")
                                else:
                                    st.error(f"❌ Hakem Reddetti (Puan: {result.judge_score}/10.0)")
                                
                                st.markdown(f"**Geri Bildirim:** {result.judge_feedback}")
                                
                                det = getattr(result, "judge_details", {})
                                if det:
                                    st.caption(f"Doğruluk: {det.get('correctness')}/10 | Niyet: {det.get('intent')}/10 | Kalite: {det.get('quality')}/10")
                            else:
                                st.info("Bulut Hakemi bu sorguda çalıştırılmadı (Basit sorgu veya Local Mod).")

                    st.session_state["messages"].append({
                        "role": "user", 
                        "type": "text", 
                        "content": user_prompt
                    })
                    
                    #  Asistan yanıtını 4 sekmeyi dolduracak TÜM BİLGİLERLE kaydediyoruz
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "type": "result",
                        "content": f"✅ İşlem Tamamlandı. (Sorgu Kategorisi: {getattr(result, 'query_category', 'bilinmiyor').upper()})",
                        "code": result.code,
                        "output": result.execution_output,
                        "error": result.execution_error,
                        # 4 Sekme için gereken diğer veriler:
                        "execution_success": getattr(result, "execution_success", False),
                        "attempts": getattr(result, "attempts", 1),
                        "csv_schema": getattr(result, "csv_schema", ""),
                        "rag_context": getattr(result, "rag_context", ""),
                        "query_category": getattr(result, "query_category", "bilinmiyor"),
                        "reviewer_issues": getattr(result, "reviewer_issues", []),
                        "reviewer_fixed": getattr(result, "reviewer_fixed", False),
                        "judge_score": getattr(result, "judge_score", None),
                        "judge_passed": getattr(result, "judge_passed", False),
                        "judge_feedback": getattr(result, "judge_feedback", ""),
                        "judge_details": getattr(result, "judge_details", {})
                    })
                    
                    

    finally:
        # İşlem bitince geçici dosyayı temizle
        if os.path.exists(tmp_path):
            os.remove(tmp_path)