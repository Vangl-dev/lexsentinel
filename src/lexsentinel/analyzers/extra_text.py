import html
import re

from lexsentinel.models import Finding
from lexsentinel.analyzers.scoring import add_finding
from lexsentinel.analyzers.prompt import detect_prompt


INFO_KEY_LABELS = {
    "/Title": "Título",
    "/Author": "Autor",
    "/Subject": "Assunto",
    "/Keywords": "Palavras-chave",
    "/Creator": "Aplicativo de criação",
    "/Producer": "Gerador do PDF",
}

_XMP_TEXT_RE = re.compile(r">([^<]+)<")


def _add_prompt_finding(result, title, text, page=None, bbox=None):
    add_finding(
        result,
        Finding(
            "prompt_injection",
            "CRITICAL",
            100,
            "HIGH",
            title,
            text[:300],
            page,
            bbox=bbox,
        ),
    )


def inspect_info_dict(result, pdf):
    for key, value in pdf.docinfo.items():
        text = str(value)
        if detect_prompt(text):
            label = INFO_KEY_LABELS.get(str(key), str(key).lstrip("/"))
            _add_prompt_finding(
                result,
                f"Prompt injection em metadados ({label})",
                text,
            )


def inspect_xmp(result, pdf):
    if "/Metadata" not in pdf.Root:
        return

    raw = pdf.Root.Metadata.read_bytes().decode("utf-8", errors="replace")

    for node in _XMP_TEXT_RE.findall(raw):
        text = html.unescape(node).strip()
        if text and detect_prompt(text):
            _add_prompt_finding(
                result,
                "Prompt injection em metadados XMP",
                text,
            )


def inspect_annotations(result, doc):
    for page_num, page in enumerate(doc, start=1):
        for annot in page.annots():
            info = annot.info
            for field in ("content", "title", "subject"):
                text = info.get(field) or ""
                if detect_prompt(text):
                    _add_prompt_finding(
                        result,
                        "Prompt injection em anotação (comentário)",
                        text,
                        page_num,
                        tuple(annot.rect),
                    )
                    break

        for widget in page.widgets():
            values = (widget.field_value, widget.field_label, widget.field_name)
            for value in values:
                text = str(value) if value else ""
                if detect_prompt(text):
                    _add_prompt_finding(
                        result,
                        "Prompt injection em campo de formulário",
                        text,
                        page_num,
                        tuple(widget.rect),
                    )
                    break


def inspect_bookmarks(result, doc):
    for _level, title, page in doc.get_toc():
        if detect_prompt(title):
            _add_prompt_finding(
                result,
                "Prompt injection em marcador (sumário)",
                title,
                page if page > 0 else None,
            )


def inspect_extra_text(result, doc, pdf):
    steps = [
        ("metadados", lambda: inspect_info_dict(result, pdf)),
        ("metadados XMP", lambda: inspect_xmp(result, pdf)),
        ("anotações e formulários", lambda: inspect_annotations(result, doc)),
        ("marcadores", lambda: inspect_bookmarks(result, doc)),
    ]
    for label, step in steps:
        try:
            step()
        except Exception as e:
            result.errors.append(f"Erro ao verificar {label}: {e}")
