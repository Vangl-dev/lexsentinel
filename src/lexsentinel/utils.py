import re
from pathlib import Path


def sanitize_filename(name: str) -> str:
    stem = Path(name).stem.lower()

    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }

    for old, new in replacements.items():
        stem = stem.replace(old, new)

    stem = re.sub(r"\s+", "_", stem)
    stem = re.sub(r"[^a-z0-9_-]", "", stem)
    stem = re.sub(r"_+", "_", stem)

    return stem.strip("_")


def default_output_name(pdf_path: str, extension="html"):
    safe = sanitize_filename(pdf_path)
    return f"{safe}_laudo_lexsentinel.{extension}"


def sanitized_output_name(pdf_path: str):
    safe = sanitize_filename(pdf_path)
    return f"{safe}_sanitizado_lexsentinel.pdf"
