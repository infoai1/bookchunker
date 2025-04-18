import streamlit as st
import pandas as pd
from utils import ensure_punkt, get_tokenizer
from file_processor import extract_sentences_with_structure
from chunker import chunk_by_tokens, chunk_by_chapter

st.set_page_config(page_title="📚 Book‑to‑Chunks", layout="wide")
st.title("📚 Book‑to‑Chunks Converter")

with st.sidebar:
    f = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])
    mode = st.radio("Chunking mode", ["~200–250 tokens (hybrid)", "By chapter heading"])
    skip0 = st.number_input("Skip pages at start (PDF)", 0, 50, 0)
    skip1 = st.number_input("Skip pages at end (PDF)", 0, 50, 0)
    first = st.number_input("First processed page#", 1, 999, 1)
    regex = st.text_input(
    "Heading regex (leave blank for font-size detection)",
    value="",
    placeholder="e.g. ^Chapter \d+",
    key="regex"
)",
                          r"^(chapter|section|part)\s+[ivxlcdm\d]+")
    go = st.button("🚀 Process")

if go and f:
    ensure_punkt()
    tokenizer = get_tokenizer()
    st.info("Extracting…")
    data = extract_sentences_with_structure(
        file_content=f.getvalue(),
        filename=f.name,
        pdf_skip_start=skip0,
        pdf_skip_end=skip1,
        pdf_first_page_offset=first,
        heading_criteria=None,
        regex=regex,
        max_heading_words=12
    )
    st.success(f"{len(data):,} sentences extracted")
    st.info("Chunking…")
    chunks = chunk_by_tokens(data, tokenizer) if mode.startswith("~") else chunk_by_chapter(data)
    st.success(f"{len(chunks):,} chunks created")
    df = pd.DataFrame(chunks, columns=["Text Chunk", "Source Marker", "Detected Title"])
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode()
    st.download_button("📥 Download CSV", csv, file_name=f"{f.name.rsplit('.',1)[0]}_chunks.csv")
else:
    st.write("👈 Upload a file & hit **Process**")
