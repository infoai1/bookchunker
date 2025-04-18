import logging
import tiktoken
from typing import List, Tuple, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

DEFAULT_TITLE = "Introduction"

def chunk_by_tokens(
    structured: List[Tuple[str, str, Optional[str]]],
    tokenizer: tiktoken.Encoding,
    target_min: int = 200,
    target_max: int = 250
) -> List[Tuple[str, str, str]]:
    tok_lens = [len(tokenizer.encode(s[0])) for s in structured]
    out, chunk, marks = [], [], []
    cur_title, tok_count = DEFAULT_TITLE, 0
    def flush(prev_overlap: int):
        nonlocal chunk, marks, tok_count
        if not chunk: return
        if tok_count < 120 and out:
            pt, pm, pttl = out.pop()
            out.append((f"{pt} " + " ".join(chunk), pm, pttl))
            chunk, marks, tok_count = [], [], 0
            return
        out.append((" ".join(chunk), marks[0], cur_title))
        overlap = chunk[-prev_overlap:]
        overlap_marks = marks[-prev_overlap:]
        chunk, marks = overlap.copy(), overlap_marks.copy()
        tok_count = sum(len(tokenizer.encode(s)) for s in chunk)
    for i, (sent, mark, heading) in enumerate(structured):
        sent_tok = tok_lens[i]
        if heading:
            flush(prev_overlap=0)
            cur_title = heading
            chunk, marks, tok_count = [sent], [mark], sent_tok
            continue
        if tok_count + sent_tok <= target_max:
            chunk.append(sent); marks.append(mark); tok_count += sent_tok
        else:
            overlap_next = 3 if tok_count >= target_max else 2
            flush(prev_overlap=overlap_next)
            chunk.append(sent); marks.append(mark); tok_count += sent_tok
    if chunk: out.append((" ".join(chunk), marks[0], cur_title))
    return out

def chunk_by_chapter(
    structured: List[Tuple[str, str, Optional[str]]]
) -> List[Tuple[str, str, str]]:
    if not structured: return []
    out, chunk, marks, cur_title = [], [], [], DEFAULT_TITLE
    for sent, mark, heading in structured:
        if heading and heading != cur_title:
            if chunk:
                out.append((" ".join(chunk), marks[0], cur_title))
            chunk, marks, cur_title = [], [], heading
        chunk.append(sent); marks.append(mark)
    out.append((" ".join(chunk), marks[0], cur_title))
    return out
