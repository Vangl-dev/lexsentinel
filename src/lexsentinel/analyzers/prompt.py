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


def is_academic_context(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ACADEMIC_MARKERS)


def detect_prompt(text: str):
    lowered = text.lower()
    for marker in PROMPT_MARKERS:
        if marker in lowered:
            return marker
    return None
