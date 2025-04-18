import logging
import nltk
import tiktoken
import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

@st.cache_resource
def ensure_punkt():
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)

@st.cache_resource
def get_tokenizer(name: str = "cl100k_base"):
    return tiktoken.get_encoding(name)
