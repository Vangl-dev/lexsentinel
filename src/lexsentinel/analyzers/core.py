import hashlib
from datetime import datetime
from pathlib import Path

import fitz
import pikepdf

from lexsentinel.models import Result, Finding, Fingerprint
from lexsentinel.analyzers.scoring import classify_risk, add_finding
from lexsentinel.analyzers.structure import inspect_structure
from lexsentinel.analyzers.semantic import inspect_semantic
from lexsentinel.analyzers.hidden_text import inspect_page
from lexsentinel.analyzers.prompt import find_prompt_matches, is_academic_context
from lexsentinel.analyzers.alt_text import inspect_alt_text
from lexsentinel.analyzers.extra_text import inspect_extra_text
from lexsentinel.evidence import generate_evidence_image


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_fingerprint(path, doc, pdf):
    file_path = Path(path)
    meta = doc.metadata or {}

    linearized = False
    try:
        linearized = "/Linearized" in pdf.trailer
    except Exception:
        pass

    return Fingerprint(
        filename=file_path.name,
        file_size=file_path.stat().st_size,
        sha256=sha256_file(path),
        pdf_version=getattr(pdf, "pdf_version", None),
        creator=meta.get("creator"),
        producer=meta.get("producer"),
        creation_date=meta.get("creationDate"),
        mod_date=meta.get("modDate"),
        encrypted=pdf.is_encrypted,
        linearized=linearized,
        page_count=doc.page_count,
    )


def analyze(path, output_html=None):
    result = Result(
        file_path=path,
        metadata={},
        analyzed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )

    try:
        doc = fitz.open(path)
    except Exception as e:
        result.errors.append(f"Falha ao abrir PDF com PyMuPDF: {e}")
        return result

    try:
        pdf = pikepdf.open(path)
    except pikepdf.PasswordError:
        result.errors.append("PDF protegido por senha.")
        return result
    except Exception as e:
        result.errors.append(f"Falha ao abrir PDF com pikepdf: {e}")
        return result

    result.metadata = {
        k: str(v)
        for k, v in (doc.metadata or {}).items()
        if v
    }

    result.fingerprint = build_fingerprint(path, doc, pdf)

    try:
        inspect_structure(result, path)
    except Exception as e:
        result.errors.append(f"Erro em structure analyzer: {e}")

    try:
        inspect_semantic(result, path)
    except Exception as e:
        result.errors.append(f"Erro em semantic analyzer: {e}")

    try:
        inspect_alt_text(result, path)
    except Exception as e:
        result.errors.append(f"Erro em alt-text analyzer: {e}")

    inspect_extra_text(result, doc, pdf)

    try:
        for page_num, page in enumerate(doc, start=1):
            inspect_page(result, page, page_num)

            spans = [
                span
                for block in page.get_text("dict").get("blocks", [])
                for line in block.get("lines", [])
                for span in line.get("spans", [])
                if span.get("text", "").strip()
            ]

            matches = find_prompt_matches([span["text"] for span in spans])

            for marker, indices in matches:
                matched = [spans[i] for i in indices]
                text = " ".join(span["text"].strip() for span in matched)

                bbox = fitz.Rect(matched[0]["bbox"])
                for span in matched[1:]:
                    bbox |= fitz.Rect(span["bbox"])

                if is_academic_context(text):
                    title = (
                        "Prompt injection potencial "
                        "(contexto acadêmico detectado)"
                    )
                else:
                    title = "Prompt injection potencial"

                add_finding(
                    result,
                    Finding(
                        "prompt_injection",
                        "CRITICAL",
                        100,
                        "HIGH",
                        title,
                        text[:300],
                        page_num,
                        bbox=tuple(bbox),
                    ),
                )

    except Exception as e:
        result.errors.append(f"Erro durante parsing de páginas: {e}")

    result.risk = classify_risk(result.total_score)

    if output_html:
        idx = 1
        for finding in result.findings:
            if finding.page and finding.bbox:
                try:
                    ev = generate_evidence_image(
                        path,
                        finding,
                        output_html,
                        idx
                    )
                    finding.evidence_path = ev
                    idx += 1
                except Exception as e:
                    result.errors.append(
                        f"Falha gerando evidência visual: {e}"
                    )

    return result
