# Local CodeGen System — Yol Haritasi & Kaynaklar

> 3 kisilik amator ekip icin Ollama + RAG + MCP tabanli local kod uretim sistemi

---

## Sistem Mimarisi (3 Modul)

```
┌─────────────────────────────┐   ┌─────────────────────────┐
│  MODUL 1: Cekirdek Motor    │   │  MODUL 2: Arayuz        │
│  Code Gen + Ollama + RAG    │   │  UI + Hedef Kullanici   │
│  + Prompt Engineering       │   │  Deneyimi               │
└──────────────┬──────────────┘   └────────────┬────────────┘
               │                                │
               └──────────┬───────────────────┘
                          │
               ┌──────────▼──────────────────┐
               │  MODUL 3: Calistirma Katmani│
               │  MCP + Execution + Isolation│
               └─────────────────────────────┘
```

---

## Yol Haritasi — 3 Asama

### ASAMA 1: Cekirdek Motor (Hafta 1-3)
**Amac:** Ollama uzerinde calisan, codebase'i anlayan RAG destekli kod uretici

- [ ] Ollama kurulumu ve model secimi (`qwen2.5-coder:32b` veya `codellama`)
- [ ] Embedding modeli secimi (`nomic-embed-text` — tamamen local)
- [ ] Vector DB kurulumu (ChromaDB veya Qdrant — local)
- [ ] Kod dosyalarini AST/tree-sitter tabanli chunking ile indexleme
- [ ] RAG pipeline olusturma (LangChain veya LlamaIndex)
- [ ] Prompt sablonlari tasarimi (system prompt, code completion, code review)
- [ ] Basit CLI uzerinden test edilebilir hale getirme
- [ ] **Cikti:** `POST /generate` endpoint'i calisan bir API

### ASAMA 2: Kullanici Arayuzu (Hafta 3-5)
**Amac:** Kullanicilarin kodla etkilesim kurabilecegi bir arayuz

- [ ] Hedef kullanici belirleme (gelistirici mi? ogrenci mi? non-tech mi?)
- [ ] UI framework secimi (Open WebUI fork / React + Tailwind / Streamlit)
- [ ] Chat arayuzu (kod highlight, markdown render)
- [ ] Dosya yukleme / repo baglama ozelligi
- [ ] Kod onizleme ve diff gosterimi
- [ ] Dark/light tema
- [ ] **Cikti:** Calisan bir web arayuzu

### ASAMA 3: Calistirma & Izolasyon (Hafta 5-7)
**Amac:** Uretilen kodun guvenli sekilde calistirilmasi

- [ ] MCP server olusturma (Python SDK / FastMCP)
- [ ] MCP tool'lari tanimlama (dosya okuma, yazma, terminal, test)
- [ ] Docker tabanli sandbox (llm-sandbox veya kendi Docker setup'i)
- [ ] Kod calistirma izolasyonu (timeout, resource limit, network kisitlama)
- [ ] Sonuc yakalama ve kullaniciya geri dondurmee
- [ ] Guvenlik testleri
- [ ] **Cikti:** `/execute` endpoint'i + MCP entegrasyonu

---

## Teknik Stack Onerisi

```
Dil:          Python 3.11+
LLM:          Ollama (qwen2.5-coder:32b / codellama:34b)
Embedding:    nomic-embed-text (Ollama uzerinden)
RAG:          LangChain + ChromaDB (baslangic icin en kolay)
MCP:          modelcontextprotocol/python-sdk (FastMCP)
Sandbox:      Docker + llm-sandbox
UI:           Streamlit (hizli prototip) veya React + Tailwind (production)
API:          FastAPI
Task Mgmt:    GitHub Projects + Issues + Milestones
```

---


### GitHub Projects Board Kolonlari

| Kolon | Aciklama |
|-------|----------|
| **Backlog** | Henuz onceliklendirilmemis fikirler |
| **Sprint** | Bu hafta yapilacaklar |
| **In Progress** | Uzerinde calisilanlar |
| **Review** | PR acik, review bekliyor |
| **Done** | Tamamlanan isler |

### Label Sistemi
- `module:core` `module:ui` `module:sandbox` — Modul bazli
- `priority:high` `priority:medium` `priority:low` — Oncelik
- `type:feature` `type:bug` `type:docs` `type:research` — Is tipi
- `good-first-issue` — Yeni baslayan icin uygun

### Milestone = Sprint
- `Sprint 1: Core MVP` (Hafta 1-3)
- `Sprint 2: UI MVP` (Hafta 3-5)
- `Sprint 3: Sandbox MVP` (Hafta 5-7)

### Otomasyon
- Issue assign edildiginde → "In Progress"a tasi
- PR merge edildiginde → "Done"a tasi
- Sub-issues kullanarak buyuk task'lari parcala

---

## Okunacak Kaynaklar & Linkler

### Ollama — Local LLM
| Kaynak | Link |
|--------|------|
| Ollama Resmi Site | https://ollama.com |
| Ollama GitHub (162k+ star) | https://github.com/ollama/ollama |
| Ollama API Dokumantasyonu | https://docs.ollama.com/api/introduction |
| Ollama Python SDK | https://github.com/ollama/ollama-python |
| Model Kutuphanesi | https://ollama.com/library |
| Kodlama icin En Iyi Modeller | https://www.codegpt.co/blog/best-ollama-model-for-coding |
| 50 Kod Ornegi ile Rehber | https://collabnix.com/the-complete-ollama-guide-2025-from-zero-to-ai-hero-with-50-code-examples/ |
| Python Entegrasyon Rehberi | https://www.cohorte.co/blog/using-ollama-with-python-step-by-step-guide |

### RAG — Retrieval Augmented Generation
| Kaynak | Link |
|--------|------|
| LangChain GitHub | https://github.com/langchain-ai/langchain |
| LlamaIndex GitHub | https://github.com/run-llama/llama_index |
| ChromaDB (Vector DB) | https://github.com/chroma-core/chroma |
| Qdrant (Vector DB) | https://github.com/qdrant/qdrant |
| RAG Teknikleri Koleksiyonu | https://github.com/NirDiamant/RAG_Techniques |
| Awesome RAG | https://github.com/Danielskry/Awesome-RAG |
| Ollama + ChromaDB RAG Rehberi | https://www.freecodecamp.org/news/build-a-local-rag-app-with-ollama-and-chromadb-in-r/ |
| Codebase RAG (Ollama Embedding) | https://medium.com/@farissyariati/ask-your-codebase-anything-using-ollama-embeddings-and-rag-c65081a5ef20 |
| LangChain + Ollama RAG | https://devblogs.microsoft.com/cosmosdb/build-a-rag-application-with-langchain-and-local-llms-powered-by-ollama/ |
| LightRAG (Graph RAG) | https://github.com/HKUDS/LightRAG |

### MCP — Model Context Protocol
| Kaynak | Link |
|--------|------|
| MCP Resmi Dokumantasyon | https://modelcontextprotocol.io |
| MCP Spesifikasyonu (2025-11-25) | https://modelcontextprotocol.io/specification/2025-11-25 |
| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk |
| MCP Server Ornekleri | https://github.com/modelcontextprotocol/servers |
| MCP Server Nasil Yazilir | https://modelcontextprotocol.io/docs/develop/build-server |
| Microsoft MCP Beginners Kursu | https://github.com/microsoft/mcp-for-beginners |
| Anthropic MCP Tanitim | https://www.anthropic.com/news/model-context-protocol |
| Anthropic MCP + Kod Calistirma | https://www.anthropic.com/engineering/code-execution-with-mcp |
| Anthropic MCP Egitimi (SkillJar) | https://anthropic.skilljar.com/introduction-to-model-context-protocol |
| Awesome MCP Servers | https://github.com/punkpeye/awesome-mcp-servers |
| MCP Ipuclari ve Tuzaklar | https://nearform.com/digital-community/implementing-model-context-protocol-mcp-tips-tricks-and-pitfalls/ |

### Kod Calistirma & Izolasyon
| Kaynak | Link |
|--------|------|
| E2B Sandbox | https://github.com/e2b-dev/E2B |
| E2B Code Interpreter | https://github.com/e2b-dev/code-interpreter |
| llm-sandbox (Docker/local) | https://github.com/vndee/llm-sandbox |
| agent-sandbox (enterprise) | https://github.com/agent-sandbox/agent-sandbox |
| Awesome Code Sandboxing | https://github.com/restyler/awesome-sandbox |
| HuggingFace Guvenli Kod Calistirma | https://huggingface.co/docs/smolagents/en/tutorials/secure_code_execution |

### Referans Projeler (Hepsini Birlestirenler)
| Kaynak | Link |
|--------|------|
| rag-code-mcp (Ollama+Qdrant+MCP) | https://github.com/doITmagic/rag-code-mcp |
| Open WebUI (Ollama UI, 124k star) | https://github.com/open-webui/open-webui |
| Continue.dev (VS Code + Ollama) | https://github.com/continuedev/continue |
| RAGFlow (Enterprise RAG) | https://github.com/infiniflow/ragflow |

### GitHub Task Management
| Kaynak | Link |
|--------|------|
| GitHub Projects Best Practices | https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects |
| Ekip Planlama Rehberi | https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/planning-and-tracking-work-for-your-team-or-project |
| Agile + GitHub Projects | https://blog.zenhub.com/how-to-use-github-agile-project-management/ |

---

## Baslangic Oncesi Okuma Sirasi (Onerilen)

Kodlamaya baslamadan once su sirayla okuyin:

1. **Ollama Quick Start** → https://ollama.com — Kurulum ve ilk model calistirma
2. **Ollama API Docs** → https://docs.ollama.com/api/introduction — API yapisini anlama
3. **RAG Nedir?** → https://github.com/NirDiamant/RAG_Techniques — Temel kavramlar
4. **ChromaDB Getting Started** → https://github.com/chroma-core/chroma — Vector DB temelleri
5. **MCP Intro** → https://modelcontextprotocol.io — Protokolu anlama
6. **MCP Server Yazma** → https://modelcontextprotocol.io/docs/develop/build-server — Pratik
7. **Kod Izolasyonu** → https://github.com/vndee/llm-sandbox — Sandbox temelleri
8. **Referans Proje** → https://github.com/doITmagic/rag-code-mcp — Hepsini birlestiren ornek

---

## Hizli Baslangiic Komutlari

```bash
# 1. Ollama kur
curl -fsSL https://ollama.com/install.sh | sh

# 2. Kod modeli indir
ollama pull qwen2.5-coder:32b

# 3. Embedding modeli indir
ollama pull nomic-embed-text

# 4. Python ortami kur
python -m venv .venv && source .venv/bin/activate

# 5. Temel paketleri yukle
pip install langchain chromadb ollama fastapi uvicorn

# 6. MCP SDK yukle
pip install mcp

# 7. Test et
ollama run qwen2.5-coder:32b "Write a Python function to reverse a string"
```

---

## Notlar

- **Donanim:** 32B model icin minimum 24GB VRAM (veya 32GB RAM + CPU offload). Daha dusuk donanim icin `qwen2.5-coder:7b` kullanin.
- **Tamamen Offline:** Tum stack internet baglantisi olmadan calisabilir (Ollama + ChromaDB + Docker).
- **Iteratif Yaklasim:** Her asamanin sonunda calisan bir MVP olsun. Kusursuz olmasin, calissin.
- **Kod Review:** Her PR en az 1 kisi tarafindan review edilsin.
- **Dokumantasyon:** Her modul icin README.md yazin. Gelecekteki siz icin.

---

*Olusturulma tarihi: 2026-02-18*
