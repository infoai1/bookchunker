import fitz
import docx, io
import re, statistics, nltk, logging
from typing import List, Tuple, Optional, Dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",)

# Basic text cleaner patterns
RE_WS       = re.compile(r"\s+")
RE_ONLY_DIG = re.compile(r"^\d{1,4}$")
RE_PNO_LEAD = re.compile(r"^\d+\s+")
RE_MID_FI   = re.compile(r"([A-Za-z])!([A-Za-z])")

# Clean a raw text block
def _clean_text(raw: str) -> str:
    txt = raw.replace("
", " ")
    # Fix split 'The' glyph if OCR dropped 'h'
    txt = txt.replace("Te ", "The ")
    txt = RE_PNO_LEAD.sub("", txt)
    txt = RE_MID_FI.sub(r"\1fi\2", txt)
    return RE_WS.sub(" ", txt).strip()

# Detect a heading
def _is_heading(text: str, regex: Optional[re.Pattern], max_words: int) -> bool:
    wc = len(text.split())
    if not (2 <= wc <= max_words):
        return False
    return True if regex is None else bool(regex.search(text))

# Extract sentences from PDF
def _extract_pdf(data: bytes, skip_start: int, skip_end: int, offset: int,
                 regex: Optional[re.Pattern], max_words: int
                 ) -> List[Tuple[str, str, Optional[str]]]:
    doc = fitz.open(stream=data, filetype="pdf")
    pages = range(skip_start, doc.page_count - skip_end)

    # Compute font-size threshold
    sizes = [
        sp["size"]
        for p in pages
        for blk in doc.load_page(p).get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]
        if blk["type"] == 0
        for ln in blk["lines"] for sp in ln["spans"]
    ]
    thr = (statistics.mean(sizes) + statistics.pstdev(sizes) * 0.5) if sizes else 0

    out: List[Tuple[str, str, Optional[str]]] = []
    for p in pages:
        page = doc.load_page(p)
        for blk in page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]:
            if blk["type"] != 0:
                continue
            raw = " ".join(sp["text"] for ln in blk["lines"] for sp in ln["spans"])
            txt = _clean_text(raw)
            if not txt or RE_ONLY_DIG.match(txt):
                continue
            fsize = max(sp["size"] for ln in blk["lines"] for sp in ln["spans"])
            heading = txt if (fsize >= thr and _is_heading(txt, regex, max_words)) else None
            for sent in nltk.sent_tokenize(txt):
                out.append((sent, f"p{p+offset}", heading))
    doc.close()
    return out

# Extract sentences from DOCX
def _extract_docx(data: bytes, regex: Optional[re.Pattern], max_words: int
                  ) -> List[Tuple[str, str, Optional[str]]]:
    doc = docx.Document(io.BytesIO(data))
    out: List[Tuple[str, str, Optional[str]]] = []
    for i, para in enumerate(doc.paragraphs, 1):
        txt = _clean_text(para.text)
        if not txt:
            continue
        heading = txt if _is_heading(txt, regex, max_words) else None
        for sent in nltk.sent_tokenize(txt):
            out.append((sent, f"para{i}", heading))
    return out

# Public API
def extract_sentences_with_structure(*,
                                     file_content: bytes,
                                     filename: str,
                                     pdf_skip_start: int = 0,
                                     pdf_skip_end: int = 0,
                                     pdf_first_page_offset: int = 1,
                                     heading_criteria: Dict = None,
                                     regex: str = "",
                                     max_heading_words: int = 12
                                     ) -> List[Tuple[str, str, Optional[str]]]:
    rx = re.compile(regex, re.I) if regex else None
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        return _extract_pdf(file_content, pdf_skip_start, pdf_skip_end,
                            pdf_first_page_offset, rx, max_heading_words)
    if ext == "docx":
        return _extract_docx(file_content, rx, max_heading_words)
    raise ValueError("Unsupported file type: " + filename)
