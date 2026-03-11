# Code Generation Reading List

> Curated articles & tutorials for the team to read before starting Phase 1 implementation.
> Focus: Local LLM code generation, RAG for code, CSV/data processing, prompt engineering.

---

## Recommended Reading Order

Start here for the fastest path to productive development:

| # | Article | Why Read This |
|---|---------|---------------|
| 1 | [RAG App with Ollama + ChromaDB (HackerNoon)](#27-build-your-own-rag-app-ollama-python-and-chromadb) | Matches our exact stack — Ollama + ChromaDB + Python |
| 2 | [AST-Based Chunking for Code RAG](#22-enhancing-llm-code-generation-with-rag-and-ast-based-chunking) | Critical for code-specific chunking strategy |
| 3 | [Structured Outputs with Ollama](#33-structured-outputs-with-ollama) | Essential for reliable pipeline output |
| 4 | [CSV Analysis with Local LLMs](#41-csv-analysis-with-local-llms) | Directly on-topic for our CSV use case |
| 5 | [Build Your Own PandasAI with LlamaIndex](#46-build-your-own-pandasai-with-llamaindex) | Our exact approach — LlamaIndex + pandas code gen |
| 6 | [LLM Testing Methods (Confident AI)](#61-llm-testing-top-methods-and-strategies) | For evaluating what we build |

---

## 1. Local LLM Code Generation with Ollama

### 1.1 Ollama Code Generation: Build Your Local AI Programming Assistant
- **URL:** https://markaicode.com/ollama-code-generation-ai-programming-assistant/
- **What you'll learn:** End-to-end guide for building a local AI programming assistant using Ollama — model selection, API usage, and Python integration patterns.
- **Difficulty:** Beginner/Intermediate

### 1.2 Building a Code Analysis Assistant with Ollama
- **URL:** https://medium.com/@igorbenav/building-a-code-analysis-assistant-with-ollama-a-step-by-step-guide-to-local-llms-3d855bc68443
- **What you'll learn:** Constructing a full code analysis assistant with Ollama and Python — analyzing code structure, identifying issues, suggesting improvements while keeping code private.
- **Difficulty:** Intermediate

### 1.3 An Entirely Open-Source AI Code Assistant Inside Your Editor
- **URL:** https://ollama.com/blog/continue-code-assistant
- **What you'll learn:** Official Ollama tutorial for integrating local LLMs with Continue extension in VS Code/JetBrains — AI-powered code completion running entirely locally.
- **Difficulty:** Beginner

### 1.4 A Guide to Self-Hosted LLM Coding Assistants
- **URL:** https://semaphore.io/blog/selfhosted-llm-coding-assistants
- **What you'll learn:** Comprehensive survey of self-hosted coding assistant options — model selection, hardware requirements, editor integrations with Ollama as the primary backend.
- **Difficulty:** Intermediate

### 1.5 Building a Local Code Assistant with Open Source LLMs
- **URL:** https://medium.com/@sayantanmanna840/building-a-local-code-assistant-with-open-source-llms-a-step-by-step-guide-085758d85d70
- **What you'll learn:** Step-by-step walkthrough covering the full stack from model setup to Python API integration and practical code generation workflows.
- **Difficulty:** Intermediate

---

## 2. RAG for Code (Code-Aware Retrieval)

### 2.1 RAG for a Codebase with 10k Repos
- **URL:** https://www.qodo.ai/blog/rag-for-large-scale-code-repos/
- **What you'll learn:** Engineering challenges of RAG for massive codebases — intelligent chunking, language-specific static analysis, metadata-enriched embeddings, scalable indexing.
- **Difficulty:** Advanced

### 2.2 Enhancing LLM Code Generation with RAG and AST-Based Chunking
- **URL:** https://vxrl.medium.com/enhancing-llm-code-generation-with-rag-and-ast-based-chunking-5b81902ae9fc
- **What you'll learn:** Why standard text chunking fails for code, and how AST-aware chunking with tree-sitter dramatically improves retrieval quality for code generation.
- **Difficulty:** Intermediate/Advanced

### 2.3 RAG for LLM Code Generation using AST-Based Chunking
- **URL:** https://medium.com/@vishnudhat/rag-for-llm-code-generation-using-ast-based-chunking-for-codebase-c55bbd60836e
- **What you'll learn:** Practical implementation of AST-based code chunking — extracting function-level and class-level chunks to preserve semantic integrity when indexing Python codebases.
- **Difficulty:** Intermediate

### 2.4 Building RAG on Codebases: Part 1 (LanceDB)
- **URL:** https://lancedb.com/blog/building-rag-on-codebases-part-1/
- **What you'll learn:** Recreating Cursor's @codebase feature from scratch using tree-sitter for AST parsing and embedding search. Covers Java, Python, Rust, and JavaScript.
- **Difficulty:** Intermediate

### 2.5 Building RAG on Codebases: Part 2 (LanceDB)
- **URL:** https://blog.lancedb.com/building-rag-on-codebases-part-2/
- **What you'll learn:** Full retrieval pipeline with separate vector tables for methods vs classes, metadata-driven filtering, and reranking with embedding models.
- **Difficulty:** Intermediate/Advanced

### 2.6 How Cursor Actually Indexes Your Codebase
- **URL:** https://towardsdatascience.com/how-cursor-actually-indexes-your-codebase/
- **What you'll learn:** Reverse-engineering analysis of Cursor's production RAG pipeline — chunking, embedding, vector storage, and privacy-preserving architecture. Excellent reference for building your own.
- **Difficulty:** Advanced

### 2.7 Build Your Own RAG App: Ollama, Python, and ChromaDB
- **URL:** https://hackernoon.com/build-your-own-rag-app-a-step-by-step-guide-to-setup-llm-locally-using-ollama-python-and-chromadb
- **What you'll learn:** Step-by-step fully local RAG application using Ollama + Python + ChromaDB — document ingestion, embedding, vector search, and query generation. **Directly matches our tech stack.**
- **Difficulty:** Beginner/Intermediate

### 2.8 Building a Simple RAG System with ChromaDB, LangChain, and Ollama
- **URL:** https://medium.com/@siddiqodiq/building-a-simple-rag-system-with-chromadb-langchain-and-local-llm-ollama-2a3e8c3d4af1
- **What you'll learn:** Hands-on tutorial combining ChromaDB, LangChain, and Ollama for a private, local RAG pipeline with code examples throughout.
- **Difficulty:** Beginner/Intermediate

---

## 3. Prompt Engineering for Code Generation

### 3.1 Prompt Engineering for Coding Tasks
- **URL:** https://towardsdatascience.com/prompt-engineering-llms-coding-chatgpt-artificial-intelligence-c16620503e4e/
- **What you'll learn:** Practical prompting strategies for code generation — specifying context, defining constraints, using in-code comments as guidance, structuring prompts for reliable output.
- **Difficulty:** Beginner/Intermediate

### 3.2 How to Write Good Prompts for Generating Code from LLMs
- **URL:** https://github.com/potpie-ai/potpie/wiki/How-to-write-good-prompts-for-generating-code-from-LLMs
- **What you'll learn:** Practitioner-focused guide covering quality context, technical specificity, generating multiple solution approaches, and comparative analysis for selecting the best implementation.
- **Difficulty:** Intermediate

### 3.3 Structured Outputs with Ollama
- **URL:** https://ollama.com/blog/structured-outputs
- **What you'll learn:** Official guide for using Ollama's structured output with Pydantic and JSON schema — critical for getting reliable, machine-parseable code generation responses from local models.
- **Difficulty:** Intermediate

### 3.4 Structured Output for Open Source and Local LLMs (Instructor Library)
- **URL:** https://python.useinstructor.com/blog/2024/03/07/open-source-local-structured-output-pydantic-json-openai/
- **What you'll learn:** Using the Instructor library with Ollama's OpenAI-compatible API to enforce Pydantic-validated structured output, eliminating parsing failures in code generation pipelines.
- **Difficulty:** Intermediate

### 3.5 Structured Chain-of-Thought Prompting for Code Generation (Paper)
- **URL:** https://arxiv.org/abs/2305.06599
- **What you'll learn:** Academic paper showing that SCoT prompting — using program structure (sequence, branch, loop) as intermediate reasoning — outperforms standard CoT by up to 13.79% on Pass@1.
- **Difficulty:** Advanced

### 3.6 Generating Code (Prompt Engineering Guide — DAIR.AI)
- **URL:** https://www.promptingguide.ai/applications/coding
- **What you'll learn:** Covers zero-shot code gen, completion, debugging, unit test generation, and code explanation — with practical prompt templates you can adapt directly.
- **Difficulty:** Beginner

---

## 4. CSV / Data Processing Code Generation

### 4.1 CSV Analysis with Local LLMs
- **URL:** https://digitalarcher.dev/csv-analysis-with-local-llms/
- **What you'll learn:** Privacy-focused tutorial combining PandasAI with local Ollama model (qwen2.5-coder) for CSV analysis — setup, querying, chart generation, and real-world limitations.
- **Difficulty:** Beginner/Intermediate

### 4.2 Enhancing Data Analysis with PandasAI and Local Llama3 LLM
- **URL:** https://medium.com/@francisofficialrnd/enhancing-data-analysis-with-pandasai-and-local-llama3-llm-a3d02fd76134
- **What you'll learn:** Setting up PandasAI with a local Llama3 model via Ollama — natural language to pandas code translation while keeping data fully local.
- **Difficulty:** Beginner/Intermediate

### 4.3 Process Pandas DataFrames with a Large Language Model
- **URL:** https://towardsdatascience.com/process-pandas-dataframes-with-a-large-language-model-8362468aca47/
- **What you'll learn:** Two approaches to LLM + Pandas: code-generation agents (LLM writes and executes Python) vs direct text-processing, with guidance on when to use each.
- **Difficulty:** Intermediate

### 4.4 Automating CSV Data Analysis with LLMs: A Comprehensive Workflow
- **URL:** https://medium.com/@mail2mhossain/automating-csv-data-analysis-with-llms-a-comprehensive-workflow-4f6d613f1dd3
- **What you'll learn:** Production-oriented workflow for LLM-driven CSV analysis — prompt intake, code generation, code sanitization, sandboxed execution, and error handling.
- **Difficulty:** Intermediate/Advanced

### 4.5 LlamaIndex Pandas Query Engine (Official Docs)
- **URL:** https://docs.llamaindex.ai/en/stable/examples/query_engine/pandas_query_engine/
- **What you'll learn:** Official LlamaIndex docs for PandasQueryEngine — converting natural language to Pandas code with safety guards, verbose mode, and local model integration.
- **Difficulty:** Beginner/Intermediate

### 4.6 Build Your Own PandasAI with LlamaIndex
- **URL:** https://www.kdnuggets.com/build-your-own-pandasai-with-llamaindex
- **What you'll learn:** Building a custom PandasAI-style system from scratch using LlamaIndex primitives — full control over prompts, code generation logic, and execution.
- **Difficulty:** Intermediate

---

## 5. Building Code Generation Pipelines (End-to-End)

### 5.1 Build a Code Generator and Executor Agent Using LangGraph
- **URL:** https://medium.com/the-ai-forum/build-a-code-generator-and-executor-agent-using-langgraph-langchain-sandbox-and-groq-kimi-k2-291a88e66e6f
- **What you'll learn:** Full LangGraph agentic workflow — generates Python code, executes safely in sandbox, self-healing loop that retries on errors. Directly applicable to CSV processing pipelines.
- **Difficulty:** Advanced

### 5.2 Build LangChain Agent with Code Interpreter (E2B)
- **URL:** https://e2b.dev/blog/build-langchain-agent-with-code-interpreter
- **What you'll learn:** Attaching a secure isolated sandbox to a LangChain agent for safe execution of LLM-generated code — run Python, install packages, process data without host risk.
- **Difficulty:** Intermediate

### 5.3 Local RAG from Scratch
- **URL:** https://towardsdatascience.com/local-rag-from-scratch-3afc6d3dea08/
- **What you'll learn:** Complete containerized local RAG system from the ground up — no managed services, no cloud APIs. Document ingestion, embedding, vector search, Flask API wrapper.
- **Difficulty:** Intermediate/Advanced

### 5.4 LlamaIndex for Beginners 2025: Zero to Production
- **URL:** https://medium.com/@gautsoni/llamaindex-for-beginners-2025-a-complete-guide-to-building-rag-apps-from-zero-to-production-cb15ad290fe0
- **What you'll learn:** Full LlamaIndex mental model (Documents → Nodes → Index → Retriever → Query Engine) from basic prototype to production-ready patterns with evaluation.
- **Difficulty:** Beginner/Intermediate

### 5.5 RAG with Ollama: 9 Essential Steps
- **URL:** https://dataskillblog.com/rag-with-ollama-tutorial
- **What you'll learn:** Concrete 9-step walkthrough — model testing, data fetching, text splitting, embedding, cosine similarity, context building, and generation with before/after comparisons.
- **Difficulty:** Beginner/Intermediate

---

## 6. Code Quality & Evaluation

### 6.1 LLM Testing: Top Methods and Strategies
- **URL:** https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies
- **What you'll learn:** Comprehensive testing playbook — unit testing, regression testing, and performance testing for LLM outputs using DeepEval framework. Directly applicable to testing generated pandas code.
- **Difficulty:** Intermediate

### 6.2 HumanEval: Evaluating LLM Code Generation Capabilities
- **URL:** https://www.datacamp.com/tutorial/humaneval-benchmark-for-evaluating-llm-code-generation-capabilities
- **What you'll learn:** Running the HumanEval benchmark against local models using Hugging Face Evaluate — computing pass@k scores and interpreting results.
- **Difficulty:** Intermediate

### 6.3 Using LLM-as-a-Judge to Evaluate LLM-Generated Code
- **URL:** https://medium.com/softtechas/utilising-llm-as-a-judge-to-evaluate-llm-generated-code-451e9631c713
- **What you'll learn:** Using a second LLM as an automated evaluator for generated code — execution-free evaluation and practical CI/CD integration.
- **Difficulty:** Intermediate/Advanced

### 6.4 What's Wrong with LLM-Generated Code? An Extensive Study
- **URL:** https://arxiv.org/html/2407.06153v1
- **What you'll learn:** Categorizes the most common failure modes — logic errors, missing edge cases, hallucinated APIs, security vulnerabilities. Concrete taxonomy for building evaluation test suites.
- **Difficulty:** Advanced

### 6.5 Evaluating RAG for Large Scale Codebases
- **URL:** https://www.qodo.ai/blog/evaluating-rag-for-large-scale-codebases/
- **What you'll learn:** Rigorous evaluation of code-specific RAG systems — metrics for retrieval quality, chunk relevance, and end-to-end answer accuracy.
- **Difficulty:** Advanced

---

## Bonus: Directly Relevant to Our Stack

| Resource | Why It Matters |
|----------|---------------|
| [RAG with Llama3, LangChain and ChromaDB (Stackademic)](https://stackademic.com/blog/rag-using-llama3-langchain-and-chromadb-77bba0154df4) | Exact stack match — LangChain + ChromaDB + local model |
| [Custom RAG Pipeline for Code Reviews (Qodo)](https://www.qodo.ai/blog/custom-rag-pipeline-for-context-powered-code-reviews/) | Production RAG design for code-specific use cases |
| [LlamaIndex Complete Guide (Galileo)](https://galileo.ai/blog/llamaindex-complete-guide-rag-data-workflows-llms) | LlamaIndex deep-dive for data workflow use cases |
| [PandasAI with Local Llama3.2 (Medium)](https://medium.com/@ashishsingh.chunar2017/unleashing-the-power-of-local-language-models-for-data-analysis-pandasai-with-llama3-2-df5a3e6c7119) | PandasAI + local LLM for data analysis |
| [LLM Prompting Techniques for Developers](https://www.pedroalonso.net/blog/llm-prompting-techniques-developers/) | Zero-shot, few-shot, CoT prompting reference with code examples |

---

*Last updated: 2026-02-18*
