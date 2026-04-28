import pandas as pd
import streamlit as st

st.set_page_config(page_title="SpendIQ Copilot", page_icon="💸", layout="wide")

st.title("SpendIQ Copilot")
st.write("App loaded. Now importing agent...")

try:
    from spendiq.agent import SpendIQAgent
    st.success("Agent import successful.")
except Exception as e:
    st.error("Agent import failed.")
    st.exception(e)
    st.stop()


@st.cache_resource(show_spinner=False)
def load_agent():
    return SpendIQAgent()


try:
    with st.spinner("Loading documents and building retrieval index..."):
        agent = load_agent()
    st.success("Agent loaded successfully.")
except Exception as e:
    st.error("Agent failed to load.")
    st.exception(e)
    st.stop()


question = st.text_area(
    "Ask SpendIQ a question:",
    value="What is total spend with Stratos Cloud Services over the last 12 months?",
    height=100,
)

if st.button("Ask SpendIQ", type="primary"):
    try:
        with st.spinner("Thinking..."):
            result = agent.answer(question)

        st.subheader("Answer")
        st.write(result.get("answer"))

        st.subheader("Tools Used")
        st.write(result.get("tools_used", []))

        rows = result.get("sql_rows", [])
        if rows:
            st.subheader("Structured Data Results")
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

        snippets = result.get("doc_snippets", [])
        if snippets:
            st.subheader("Document Evidence")
            for i, doc in enumerate(snippets, start=1):
                with st.expander(f"Source {i}: {doc.get('source')}"):
                    st.write(f"Score: {doc.get('score', 0):.4f}")
                    st.write(doc.get("text", "")[:1500])

        st.subheader("Sources")
        st.json(result.get("sources", {}))

    except Exception as e:
        st.error("Question failed.")
        st.exception(e)