"""Interactive CLI for testing code generation."""
import argparse
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer
from src.rag.hybrid_retriever import HybridRetriever

def main():
    # Komut satırı argümanlarını tanımlıyoruz
    parser = argparse.ArgumentParser(description="Enclave CodeRunner CLI")
    parser.add_argument("--csv", help="İşlenecek CSV dosyasının yolu")
    parser.add_argument("--prompt", help="Üretim için sorunuz (Boş bırakılırsa interaktif mod açılır)")
    parser.add_argument("--index", action="store_true", help="Bilgi bankasını (RAG) günceller ve çıkar")
    
    args = parser.parse_args()

    # 1. Güncelleme Modu
    if args.index:
        print("Bilgi bankası güncelleniyor...")
        indexer = KnowledgeIndexer()
        indexer.index_knowledge_dir(force_reindex=True)

        retriever = HybridRetriever(use_llm_reranker=False)
        retriever.build_bm25_index(force=True)

        print(f"Tamamlandı. İstatistikler: {indexer.get_stats()}")
        return

    # Eğer --index kullanılmadıysa, mutlaka bir CSV dosyası belirtilmiş olmalıdır
    if not args.csv:
        print("Hata: --csv parametresi ile bir dosya yolu belirtmelisiniz.")
        print("Kullanım örneği: python cli.py --csv data/sample_csvs/sales_data.csv")
        return

    # Orkestra Şefini (Pipeline) Başlat
    pipeline = CodePipeline()

    # 2. Tek Atışlık Mod
    if args.prompt:
        result = pipeline.generate(args.csv, args.prompt)
        print(result.code)
    
    # 3. İnteraktif (Chat) Mod
    else:
        print(f"CSV yüklendi: {args.csv}")
        print("Sorularınızı yazın (Çıkmak için Ctrl+C tuşlarına basın):\n")
        print("İpucu: Önceki sonuçlara atıfta bulunabilirsiniz (örn: 'şimdi bunu bar grafiği yap').\n")
        
        session_id = None
        next_turn = 1
        while True:
            try:
                # Kullanıcıdan girdi al
                prompt_text = f"[Tur {next_turn}] >>> " if session_id else ">>> "
                prompt = input(prompt_text)
                
                # Boş enter basılırsa atla
                if not prompt.strip():
                    continue
                
                # Kodu üret ve çalıştır
                result = pipeline.generate(args.csv, prompt, session_id=session_id)

                session_id = result.session_id
                next_turn = result.turn_number + 1
                
                if result.turn_number > 1:
                    print(f"  (🧠 Tur {result.turn_number - 1} üzerine inşa ediliyor...)")
                
                print("\n" + "="*40)
                print("💻 ÜRETİLEN KOD:")
                print("="*40)
                print(result.code)
                
                print("\n" + "="*40)
                print("📊 ÇALIŞTIRMA SONUCU (TERMINAL):")
                print("="*40)
                
                if result.execution_success:
                    print(result.execution_output if result.execution_output.strip() else "(Kod başarıyla çalıştı ancak ekrana bir şey yazdırmadı.)")
                else:
                    print("❌ HATA ALINDI:")
                    print(result.execution_error)
                
                print("\n" + "-"*40)
                
            except KeyboardInterrupt:
                # Kullanıcı Ctrl+C yaparsa zarifçe kapan
                print("\nGörüşmek üzere!")
                break
if __name__ == "__main__":
    main()