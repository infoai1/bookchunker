import streamlit as st
import pandas as pd
import re, ftfy, json, os

from utils import ensure_punkt, get_tokenizer
from file_processor import extract_sentences_with_structure
from chunker import chunk_by_tokens, chunk_by_chapter

# ────────────────────────────────────────────────────────────────
# Load your domain map (but we’ll only apply it on review, not automatically)
GLYPH_MAP_PATH = os.path.join(os.path.dirname(__file__), "glyph_map.json")
try:
    with open(GLYPH_MAP_PATH, "r", encoding="utf-8") as f:
        DOMAIN_MAP = json.load(f)
except FileNotFoundError:
    DOMAIN_MAP = {}

# Regex for raw‑glyph detection
BROKEN_GLYP = re.compile(r"\b\w*!+\w*\b")

# Simple ftfy + page‑no + letter!letter cleaner
RE_PNO    = re.compile(r"^\d+\s+")
RE_MID_FI = re.compile(r"([A-Za-z])!([A-Za-z])")

def clean_chunk(raw: str) -> str:
    t = ftfy.fix_text(raw)
    t = t.replace("\n", " ")
    t = RE_PNO.sub("", t)
    t = RE_MID_FI.sub(r"\1fi\2", t)
    # ⚠️ We DO NOT apply DOMAIN_MAP here automatically
    return re.sub(r"\s+", " ", t).strip()


# ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="📚 Book‑to‑Chunks", layout="wide")
st.title("📚 Book‑to‑Chunks Converter")

with st.sidebar:
    f     = st.file_uploader("Upload PDF or DOCX", type=["pdf","docx"])
    mode  = st.radio("Chunking mode", ["~200–250 tokens (hybrid)","By chapter heading"])
    skip0 = st.number_input("Skip pages at start (PDF)", 0, 50, 0)
    skip1 = st.number_input("Skip pages at end (PDF)",   0, 50, 0)
    first = st.number_input("First processed page#",     1, 999, 1)
    regex = st.text_input("Heading regex (blank = font‑size only)",
                          r"^(chapter|section|part)\s+[ivxlcdm\d]+")
    go    = st.button("🚀 Process")

if go and f:
    # 1) extraction
    ensure_punkt()
    tok = get_tokenizer()
    st.info("Extracting…")
    raw_structured = extract_sentences_with_structure(
        file_content = f.getvalue(),
        filename     = f.name,
        pdf_skip_start         = skip0,
        pdf_skip_end           = skip1,
        pdf_first_page_offset  = first,
        heading_criteria       = None,
        regex                  = regex,
        max_heading_words      = 12
    )

    # 2) chunking
    st.info("Chunking…")
    chunks = (chunk_by_tokens(raw_structured, tok)
              if mode.startswith("~") else
              chunk_by_chapter(raw_structured))
    st.success(f"{len(chunks):,} chunks created")

    # 3) build DataFrame with both raw and cleaned text
    df = pd.DataFrame(chunks, columns=["Raw Chunk","Source Marker","Detected Title"])
    df["Text Chunk"]    = df["Raw Chunk"].map(clean_chunk)
    df["Glyph Detected"]= df["Raw Chunk"].map(lambda x: ", ".join(set(BROKEN_GLYP.findall(x))))

    # 4) if any glyphs remain, force a quick review
    if df["Glyph Detected"].any():
        st.warning("⚠️ Some chunks contain un‑mapped ligatures — please review below")
        st.dataframe(df[df["Glyph Detected"]!=""], use_container_width=True)
        st.stop()

    # 5) Display & download
    st.dataframe(df[["Text Chunk","Source Marker","Detected Title"]], use_container_width=True)
    csv = df[["Text Chunk","Source Marker","Detected Title"]].to_csv(index=False).encode()
    st.download_button("📥 Download CSV", csv,
                       file_name=f"{f.name.rsplit('.',1)[0]}_chunks.csv")
else:
    st.write("👈 Upload a file & hit **Process**")
