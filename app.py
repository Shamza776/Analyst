import streamlit as st
import pandas as pd
import tempfile
import os

from utils import load_file, detect_key_column
from comparator import get_summary, find_missing_in_b, find_missing_in_a, find_value_mismatches
from llm_agent import generate_pandas_code, synthesize_result, synthesize_summary
from executor import run_generated_code

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Excel Comparator", page_icon="📊", layout="wide")
st.title("📊 Excel File Comparator")
st.caption("Upload two Excel files, compare them, and ask questions in plain English.")

# ── Session State ─────────────────────────────────────────────────────────────
if "df_a" not in st.session_state:
    st.session_state.df_a = None
if "df_b" not in st.session_state:
    st.session_state.df_b = None
if "key_column" not in st.session_state:
    st.session_state.key_column = None
if "summary_done" not in st.session_state:
    st.session_state.summary_done = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Sidebar: File Upload ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("📁 Upload Files")
    file_a = st.file_uploader("File A (Master / Source)", type=["xlsx", "csv"])
    file_b = st.file_uploader("File B (To Compare Against)", type=["xlsx", "csv"])

    if file_a and file_b:
        # Save uploads to temp files so pandas can read them
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_a:
            tmp_a.write(file_a.read())
            path_a = tmp_a.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_b:
            tmp_b.write(file_b.read())
            path_b = tmp_b.name

        df_a = load_file(path_a)
        df_b = load_file(path_b)
        st.session_state.df_a = df_a
        st.session_state.df_b = df_b

        # Auto-detect key column
        auto_key = detect_key_column(df_a, df_b)
        common_cols = list(set(df_a.columns) & set(df_b.columns))

        st.subheader("🔑 Key Column")
        st.caption("Column used to match rows between files")
        selected_key = st.selectbox(
            "Select key column",
            options=common_cols,
            index=common_cols.index(auto_key) if auto_key in common_cols else 0
        )
        st.session_state.key_column = selected_key

        if st.button("▶️ Run Comparison", use_container_width=True, type="primary"):
            st.session_state.summary_done = False
            st.session_state.messages = []
            st.rerun()

    st.divider()
    # st.caption("Built with Pandas + Gemini API + Streamlit")

# ── Main Area ─────────────────────────────────────────────────────────────────
df_a = st.session_state.df_a
df_b = st.session_state.df_b
key = st.session_state.key_column

if df_a is None or df_b is None:
    st.info("👈 Upload both Excel files in the sidebar to get started.")
    st.stop()

# ── Auto-run Summary on Load ──────────────────────────────────────────────────
if not st.session_state.summary_done:
    with st.spinner("Running comparison..."):
        summary = get_summary(df_a, df_b, key)
        narrative = synthesize_summary(summary, key)
        st.session_state.summary = summary
        st.session_state.narrative = narrative
        st.session_state.summary_done = True

# ── Summary Cards ─────────────────────────────────────────────────────────────
summary = st.session_state.summary

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📄 Rows in A", summary["total_in_A"])
col2.metric("📄 Rows in B", summary["total_in_B"])
col3.metric("✅ Common", summary["common_records"])
col4.metric("⚠️ Missing in B", summary["missing_in_B"])
col5.metric("⚠️ Missing in A", summary["missing_in_A"])

st.info(st.session_state.narrative)

# ── Tabs: Detailed Results ────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Missing in B", "📋 Missing in A", "🔄 Value Mismatches", "🗂️ Raw Data"
])

with tab1:
    result = find_missing_in_b(df_a, df_b, key)
    st.write(f"**{len(result)} records** in File A not found in File B")
    st.dataframe(result, use_container_width=True)

with tab2:
    result = find_missing_in_a(df_a, df_b, key)
    st.write(f"**{len(result)} records** in File B not found in File A")
    st.dataframe(result, use_container_width=True)

with tab3:
    result = find_value_mismatches(df_a, df_b, key)
    st.write(f"**{len(result)} records** with matching keys but different values")
    st.dataframe(result, use_container_width=True)

with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.caption("File A")
        st.dataframe(df_a, use_container_width=True)
    with c2:
        st.caption("File B")
        st.dataframe(df_b, use_container_width=True)

# ── Chat Interface ────────────────────────────────────────────────────────────
st.divider()
st.subheader("💬 Ask Questions About Your Data")
st.caption("Examples: *'Which vendors are missing in B?'* · *'Show mismatches in contract_value'* · *'How many records are in Nairobi in file A?'*")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "dataframe" in msg:
            st.dataframe(msg["dataframe"], use_container_width=True)

# Chat input
if prompt := st.chat_input("Ask anything about your data..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and run pandas code
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Step 1: LLM generates code
            code = generate_pandas_code(prompt, df_a, df_b, key)

            # Step 2: Execute the code safely
            success, result, error = run_generated_code(code, df_a, df_b)

            if not success:
                response = f"⚠️ I ran into an issue computing that. Error: `{error}`"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                # Step 3: LLM synthesizes the result into plain English
                narrative = synthesize_result(prompt, result)
                st.markdown(narrative)

                # Show DataFrame results visually if applicable
                msg_entry = {"role": "assistant", "content": narrative}
                if isinstance(result, pd.DataFrame) and not result.empty:
                    st.dataframe(result, use_container_width=True)
                    msg_entry["dataframe"] = result

                st.session_state.messages.append(msg_entry)