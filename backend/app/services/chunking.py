import re
from typing import List, Dict

_ABBREVIATIONS = (
    "e.g.", "i.e.", "etc.", "vs.", "approx.", "dr.", "mr.", "mrs.", "ms.",
    "prof.", "inc.", "ltd.", "corp.", "co.", "no.", "ref.", "fig.", "u.s.", "u.k."
)

# Split on newlines inside bullet/list sections or sentence terminators followed by whitespace + uppercase/digit/quote
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def _split_long_unit(unit: str, max_chars: int, word_overlap_chars: int = 60) -> List[str]:
    """Split an oversized sentence on word boundaries without breaking words."""
    words = unit.split()
    if not words:
        return []

    pieces: List[str] = []
    current_words: List[str] = []
    current_len = 0

    for word in words:
        extra = len(word) + (1 if current_words else 0)
        if current_len + extra <= max_chars or not current_words:
            current_words.append(word)
            current_len += extra
        else:
            pieces.append(" ".join(current_words))
            # Seed next piece with trailing words up to word_overlap_chars
            overlap_words: List[str] = []
            overlap_len = 0
            for prev_w in reversed(current_words):
                add_len = len(prev_w) + (1 if overlap_words else 0)
                if overlap_len + add_len > word_overlap_chars:
                    break
                overlap_words.insert(0, prev_w)
                overlap_len += add_len
            current_words = overlap_words + [word]
            current_len = sum(len(w) for w in current_words) + max(0, len(current_words) - 1)

    if current_words:
        pieces.append(" ".join(current_words))
    return pieces


def _split_sentences(paragraph: str) -> List[str]:
    """Split a paragraph into sentence/line units without breaking common abbreviations or decimals."""
    lines = [ln.strip() for ln in paragraph.splitlines() if ln.strip()]
    units: List[str] = []

    for line in lines:
        raw_parts = _SENTENCE_SPLIT_RE.split(line)
        merged: List[str] = []
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            if merged and merged[-1].lower().endswith(_ABBREVIATIONS):
                merged[-1] = f"{merged[-1]} {part}"
            else:
                merged.append(part)
        units.extend(merged)

    return units


def chunk_text(
    text: str,
    max_chars: int = 550,
    overlap_sentences: int = 1
) -> List[Dict[str, object]]:
    """
    Split text into coherent chunks aligned to paragraph and sentence boundaries.

    Returns a list of dicts: [{"chunk_index": int, "text": str}, ...].
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text.strip()) if p.strip()]
    units: List[str] = []
    for para in paragraphs:
        for sent in _split_sentences(para):
            if len(sent) > max_chars:
                units.extend(_split_long_unit(sent, max_chars=max_chars))
            else:
                units.append(sent)

    if not units:
        return []

    chunks: List[Dict[str, object]] = []
    current_units: List[str] = []
    current_len = 0
    max_overlap_chars = max_chars // 3

    for unit in units:
        sep = 1 if current_units else 0
        if current_len + sep + len(unit) <= max_chars:
            current_units.append(unit)
            current_len += sep + len(unit)
        else:
            if current_units:
                chunks.append({"chunk_index": len(chunks), "text": " ".join(current_units).strip()})

            # Build sentence-boundary overlap from tail of previous chunk
            overlap_buf: List[str] = []
            overlap_len = 0
            if overlap_sentences > 0:
                for prev in reversed(current_units[-overlap_sentences:]):
                    add_len = len(prev) + (1 if overlap_buf else 0)
                    if overlap_len + add_len + 1 + len(unit) <= max_chars and overlap_len + add_len <= max_overlap_chars:
                        overlap_buf.insert(0, prev)
                        overlap_len += add_len

            current_units = overlap_buf + [unit]
            current_len = sum(len(u) for u in current_units) + max(0, len(current_units) - 1)

    if current_units:
        chunks.append({"chunk_index": len(chunks), "text": " ".join(current_units).strip()})

    return chunks


def chunk_text_fixed(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, object]]:
    """Legacy fixed character-window chunker retained for baseline RAG evaluation comparisons."""
    if not text or not text.strip():
        return []
    step = max(1, chunk_size - overlap)
    chunks: List[Dict[str, object]] = []
    start = 0
    while start < len(text):
        snippet = text[start:start + chunk_size].strip()
        if snippet:
            chunks.append({"chunk_index": len(chunks), "text": snippet})
        start += step
    return chunks


def extract_verifiable_claims(proposal_text: str, max_claims: int = 16) -> List[str]:
    """Extract substantive proposal sentences and sub-clauses for claim-level RAG lookup."""
    if not proposal_text:
        return []
    raw_segments = re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z0-9\"'])", proposal_text)
    expanded_segments: List[str] = []
    for seg in raw_segments:
        cleaned = seg.strip().lstrip("-*#> ").strip()
        if len(cleaned) > 85:
            # Break long compound sentences on semicolons or clause boundaries while keeping the full sentence too
            expanded_segments.append(cleaned)
            sub_clauses = re.split(r"\s*;\s+|,\s+(?=(?:ISO|SOC|FedRAMP|Cyber|AWS|PostgreSQL|React|Python|API|achieving|backed|indexed|migrated|with\s+\d)\b)", cleaned)
            if len(sub_clauses) > 1:
                expanded_segments.extend(sub_clauses)
        else:
            expanded_segments.append(cleaned)

    claims: List[str] = []
    seen = set()
    for seg in expanded_segments:
        cleaned = seg.strip().lstrip("-*#> ").strip()
        if len(cleaned) < 22 or set(cleaned) <= set("|-: "):
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            claims.append(cleaned[:350])
        if len(claims) >= max_claims:
            break
    return claims
