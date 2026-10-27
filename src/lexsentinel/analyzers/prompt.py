import re
import unicodedata

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


def _remove_invisible(text: str) -> str:
    # Remove caracteres de formatação invisíveis (categoria Unicode Cf),
    # como zero-width space (U+200B), zero-width joiner e soft hyphen,
    # usados para quebrar a comparação sem alterar o texto exibido.
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


def _fold_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_for_detection(text: str) -> str:
    # NFKC converte variantes de compatibilidade (letras de largura
    # total, ligaduras, letras matemáticas) para a forma comum.
    text = unicodedata.normalize("NFKC", _remove_invisible(text))
    lowered = text.lower()
    return _WHITESPACE_RE.sub(" ", lowered)


_FOLDED_MARKERS = [(marker, _fold_accents(marker)) for marker in PROMPT_MARKERS]


def is_academic_context(text: str) -> bool:
    normalized = normalize_for_detection(text)
    return any(marker in normalized for marker in ACADEMIC_MARKERS)


def detect_prompt(text: str):
    folded = _fold_accents(normalize_for_detection(text))
    for marker, folded_marker in _FOLDED_MARKERS:
        if folded_marker in folded:
            return marker
    return None


def find_prompt_matches(texts):
    """Procura marcadores no texto formado pela sequência ``texts``.

    Detecta instruções divididas entre trechos consecutivos (spans de uma
    página, por exemplo). Retorna uma lista de ``(marcador, índices)``, em
    que ``índices`` são as posições em ``texts`` que contêm a ocorrência.
    """
    pieces = []
    offsets = []
    position = 0
    for i, text in enumerate(texts):
        piece = _fold_accents(normalize_for_detection(text)).strip()
        if not piece:
            continue
        pieces.append(piece)
        offsets.append((position, position + len(piece), i))
        position += len(piece) + 1

    joined = " ".join(pieces)

    groups = []
    for marker, folded_marker in _FOLDED_MARKERS:
        start = joined.find(folded_marker)
        while start != -1:
            end = start + len(folded_marker)
            indices = tuple(i for s, e, i in offsets if s < end and e > start)
            if not any(set(indices) <= set(seen) for _, seen in groups):
                groups = [(m, g) for m, g in groups if not set(g) <= set(indices)]
                groups.append((marker, indices))
            start = joined.find(folded_marker, start + 1)

    return sorted(groups, key=lambda group: group[1])
