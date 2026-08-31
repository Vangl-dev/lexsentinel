import re

ACADEMIC_MARKERS = [
    "arxiv",
    "doi",
    "neurips",
    "ieee",
    "acm",
    "journal",
    "bibliografia",
    "references",
    "et al",
]

PROMPT_MARKERS = [
    "ignore previous instructions",
    "ignore previous prompt",
    "system:",
    "developer:",
    "assistant:",
    "act as",
    "override",
    "aja como",
    "ignore instruções",
    "não revele",
    "não impugne",
]

_WHITESPACE_RE = re.compile(r"[\s\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")


def normalize_for_detection(text: str) -> str:
    lowered = text.lower()
    return _WHITESPACE_RE.sub(" ", lowered)


def is_academic_context(text: str) -> bool:
    normalized = normalize_for_detection(text)
    return any(marker in normalized for marker in ACADEMIC_MARKERS)


def detect_prompt(text: str):
    normalized = normalize_for_detection(text)
    for marker in PROMPT_MARKERS:
        if marker in normalized:
            return marker
    return None
