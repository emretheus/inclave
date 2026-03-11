"""
Enclave CodeRunner — Streamlit Demo UI
Run: streamlit run streamlit_demo.py
"""
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.csv_engine.schema_analyzer import SchemaAnalyzer
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer
from src.rag.few_shot_store import FewShotStore

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Enclave CodeRunner",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border: 1px solid #3d3d5c;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-card h3 { margin: 0; font-size: 2rem; color: #a6e3a1; }
    .metric-card p { margin: 0; font-size: 0.85rem; color: #bac2de; }
    .issue-badge {
        background: #f38ba8;
        color: #1e1e2e;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin: 2px 0;
    }
    .success-box {
        background: #1e3a2f;
        border: 1px solid #a6e3a1;
        border-radius: 8px;
        padding: 1rem;
    }
    .error-box {
        background: #3a1e1e;
        border: 1px solid #f38ba8;
        border-radius: 8px;
        padding: 1rem;
    }
    div[data-testid="stTabs"] button {
        font-size: 0.9rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Cached singletons
# ---------------------------------------------------------------------------
@st.cache_resource
def get_pipeline():
    indexer = KnowledgeIndexer()
    if indexer.get_stats()["total_chunks"] == 0:
        indexer.index_knowledge_dir()
    return CodePipeline(auto_execute=False)


@st.cache_resource
def get_analyzer():
    return SchemaAnalyzer()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🧬 Enclave CodeRunner")
    st.caption("Local AI-powered CSV code generator")
    st.divider()

    # System status
    pipeline = get_pipeline()
    ollama_ok = pipeline.generator.health_check()

    if ollama_ok:
        st.success("Ollama: Connected", icon="🟢")
    else:
        st.error("Ollama: Unreachable", icon="🔴")
        st.info("Run `ollama serve` in a terminal to start.")

    rag_stats = KnowledgeIndexer().get_stats()
    st.metric("RAG Chunks", rag_stats["total_chunks"])

    try:
        few_shot_count = FewShotStore().count()
        st.metric("Few-Shot Examples", few_shot_count)
    except Exception:
        st.metric("Few-Shot Examples", 0)

    st.divider()

    auto_execute = st.toggle("Auto-execute generated code", value=True)
    st.caption(
        "When enabled, code runs automatically and errors are self-healed (max 3 attempts)."
    )

    st.divider()
    st.caption("Built with Ollama + ChromaDB + FastAPI")


# ---------------------------------------------------------------------------
# Main area — CSV upload
# ---------------------------------------------------------------------------
st.header("Upload CSV & Generate Code")

col_upload, col_sample = st.columns([3, 1])

with col_upload:
    uploaded_file = st.file_uploader(
        "Upload your CSV file",
        type=["csv"],
        help="Max 200MB",
    )

with col_sample:
    st.write("")
    st.write("")
    use_sample = st.button("📂 Use Sample Dataset", use_container_width=True)

# Resolve CSV path
csv_path = None
csv_df = None

if use_sample:
    csv_path = "data/sample_csvs/sales_data.csv"
    st.session_state["csv_path"] = csv_path
elif uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded_file.getvalue())
        csv_path = tmp.name
    st.session_state["csv_path"] = csv_path
elif "csv_path" in st.session_state:
    csv_path = st.session_state["csv_path"]

if csv_path and Path(csv_path).exists():
    # Analyze
    analyzer = get_analyzer()
    schema = analyzer.analyze(csv_path)
    csv_df = pd.read_csv(csv_path)

    # -----------------------------------------------------------------------
    # Metric cards
    # -----------------------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f'<div class="metric-card"><h3>{schema.rows:,}</h3><p>Rows</p></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-card"><h3>{schema.columns}</h3><p>Columns</p></div>',
            unsafe_allow_html=True,
        )
    with m3:
        null_cols = sum(1 for c in schema.column_info if c.null_pct > 0)
        st.markdown(
            f'<div class="metric-card"><h3>{null_cols}</h3><p>Cols with Nulls</p></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="metric-card"><h3>{len(schema.potential_issues)}</h3><p>Issues Found</p></div>',
            unsafe_allow_html=True,
        )

    st.write("")

    # -----------------------------------------------------------------------
    # Tabs
    # -----------------------------------------------------------------------
    tab_cols, tab_issues, tab_preview, tab_prompt, tab_gen, tab_fewshot = st.tabs(
        ["🔍 Column Details", "⚠️ Issues", "📄 Data Preview", "📋 Prompt Preview", "🤖 Code Generation", "🧠 Few-Shot Memory"]
    )

    # --- Column Details ---
    with tab_cols:
        col_data = []
        for c in schema.column_info:
            row = {
                "Column": c.name,
                "Type": c.dtype,
                "Suggested": c.suggested_type or "—",
                "Null %": f"{c.null_pct:.1f}%",
                "Unique": c.unique_count,
                "Samples": ", ".join(str(v) for v in c.sample_values[:3]),
            }
            if c.min_val is not None:
                row["Range"] = f"{c.min_val} – {c.max_val}"
                row["Mean"] = f"{c.mean_val:.1f}"
            else:
                row["Range"] = "—"
                row["Mean"] = "—"
            col_data.append(row)
        st.dataframe(pd.DataFrame(col_data), use_container_width=True, hide_index=True)

    # --- Issues ---
    with tab_issues:
        if schema.potential_issues:
            for issue in schema.potential_issues:
                st.markdown(
                    f'<span class="issue-badge">{issue}</span>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("No issues detected!")

    # --- Data Preview ---
    with tab_preview:
        st.dataframe(csv_df.head(20), use_container_width=True)

    # --- Prompt Preview ---
    with tab_prompt:
        st.code(schema.to_prompt_string(), language="text")

    # --- Code Generation ---
    with tab_gen:
        PRESET_PROMPTS = {
            "📊 Basic Stats": "Show descriptive statistics for all numeric columns",
            "🔍 Null Analysis": "Show null counts and percentages, suggest how to handle them",
            "📈 Distribution": "Plot histogram for each numeric column",
            "🔗 Correlation": "Show correlation matrix heatmap for numeric columns",
            "📋 Top Values": "Show value counts for each categorical column",
            "🗑️ Remove Duplicates": "Find and remove duplicate rows, show count before and after",
            "📅 Parse Dates": "Convert date columns to datetime and show monthly aggregation",
            "💰 Revenue by City": "Group by city and show total revenue per city as a bar chart",
        }

        if "user_prompt" not in st.session_state:
            st.session_state["user_prompt"] = ""

        st.write("**Quick prompts:**")
        prompt_cols = st.columns(4)
        for i, (label, prompt_text) in enumerate(PRESET_PROMPTS.items()):
            with prompt_cols[i % 4]:
                if st.button(label, use_container_width=True, key=f"preset_{i}"):
                    st.session_state["user_prompt"] = prompt_text

        user_prompt = st.text_area(
            "Or write your own prompt:",
            key="user_prompt",
            height=100,
            placeholder="e.g. Group by city and show total revenue per city",
        )

        gen_col1, gen_col2 = st.columns([1, 4])
        with gen_col1:
            generate_btn = st.button(
                "🚀 Generate", type="primary", use_container_width=True
            )

        if generate_btn and user_prompt.strip():
            pipeline.auto_execute = auto_execute

            with st.spinner("Generating code..."):
                result = pipeline.generate(csv_path, user_prompt.strip())

            st.subheader("Generated Code")
            st.code(result.code, language="python")

            if auto_execute and result.execution_success is not None:
                if result.execution_success:
                    st.markdown(
                        f'<div class="success-box">✅ Code executed successfully! '
                        f"({result.attempts} attempt{'s' if result.attempts > 1 else ''})</div>",
                        unsafe_allow_html=True,
                    )
                    if result.plot_paths:
                        st.subheader("Generated Plots")
                        for plot_path in result.plot_paths:
                            st.image(plot_path, use_container_width=True)
                    if result.execution_output:
                        st.subheader("Output")
                        st.code(result.execution_output, language="text")
                else:
                    st.markdown(
                        f'<div class="error-box">❌ Code failed after {result.attempts} attempts</div>',
                        unsafe_allow_html=True,
                    )

            with st.expander("🔧 Debug Info"):
                st.write(f"**RAG context used:** {'Yes' if result.rag_context else 'No'}")
                if result.rag_context:
                    st.code(result.rag_context[:500], language="text")
                st.write("**Full prompt sent to LLM:**")
                st.code(result.full_prompt[:1000], language="text")

        elif generate_btn:
            st.warning("Please enter a prompt first.")

    # --- Few-Shot Memory ---
    with tab_fewshot:
        few_shot = FewShotStore()

        st.markdown(
            """
**How Few-Shot Memory works:**
1. You generate code with a prompt → code runs successfully
2. The query + code pair is **automatically saved** to memory
3. Next time a **similar** query comes in, the saved example is injected into the LLM prompt
4. LLM sees a proven working example → generates better code

You can also **manually add** examples below to teach the system.
"""
        )

        st.divider()

        # --- Manual Training ---
        st.subheader("Teach the System")
        with st.form("train_form", clear_on_submit=True):
            train_query = st.text_input(
                "Query",
                placeholder="e.g. Group by city and show total revenue",
            )
            train_code = st.text_area(
                "Working code",
                height=200,
                placeholder="import pandas as pd\ndf = pd.read_csv(csv_path)\n...",
            )
            submitted = st.form_submit_button(
                "💾 Save Example", type="primary"
            )
            if submitted and train_query.strip() and train_code.strip():
                few_shot.save(
                    query=train_query.strip(),
                    schema_summary="manual training",
                    code=train_code.strip(),
                )
                st.success(f"Saved! Total examples: {few_shot.count()}")
            elif submitted:
                st.warning("Both query and code are required.")

        st.divider()

        # --- Stored Examples ---
        st.subheader(f"Stored Examples ({few_shot.count()})")

        examples = few_shot.list_all()
        if not examples:
            st.info("No examples yet. Generate code or add manually above.")
        else:
            for idx, ex in enumerate(examples):
                with st.expander(f"📝 {ex['query'][:80]}", expanded=False):
                    st.code(ex["code"], language="python")
                    if st.button(
                        "🗑️ Delete",
                        key=f"del_{ex['id']}_{idx}",
                    ):
                        few_shot.delete(ex["id"])
                        st.rerun()

else:
    st.info("👆 Upload a CSV file or use the sample dataset to get started.")
