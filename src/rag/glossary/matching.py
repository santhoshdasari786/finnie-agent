import re

_LEAD = re.compile(
    r"^(?:what\s+is|what\s+are|what's|whats|define|definition\s+of|"
    r"meaning\s+of|explain|tell\s+me\s+about)(?:\s+|$)", re.I)
_MEANS = re.compile(r"^what\s+does\s+(.+?)\s+mean$", re.I)
_ARTICLE = re.compile(r"^(?:a|an|the)(?:\s+|$)", re.I)

MAX_TERM_WORDS = 5          # longer → it's a real question, not a term

def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s&/%-]", " ", text)       # drop ? . , etc, keep & / % -
    return re.sub(r"\s+", " ", text).strip()

def extract_candidate(question: str) -> str | None:
    q = question.strip().rstrip("?.! ").strip()
    m = _MEANS.match(q)
    if m:
        q = m.group(1)
    else:
        q = _LEAD.sub("", q)
    q = _ARTICLE.sub("", q)
    cand = normalize(q)
    if not cand or len(cand.split()) > MAX_TERM_WORDS:
        return None
    return cand
