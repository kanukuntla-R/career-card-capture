import re

QUESTION_STARTERS = re.compile(
    r"^(what|why|how|who|when|where|which|would|could|can|do|does|did|is|are|will|should)\b",
    re.IGNORECASE,
)


def classify_text(text: str) -> str:
    """Conservatively suggest a card type without rewriting the OCR text."""
    normalized = text.strip()
    if not normalized:
        return "UNKNOWN"
    if normalized.endswith("?") or QUESTION_STARTERS.match(normalized):
        return "QUESTION"
    word_count = len(normalized.split())
    if word_count <= 8 and len(normalized) <= 100:
        return "EMPLOYER"
    return "UNKNOWN"
