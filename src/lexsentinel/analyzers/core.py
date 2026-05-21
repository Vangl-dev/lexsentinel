import hashlib
from pathlib import Path

import fitz
import pikepdf

from lexsentinel.models import Result, Finding, Fingerprint
from lexsentinel.analyzers.scoring import classify_risk, add_finding
from lexsentinel.analyzers.structure import inspect_structure
from lexsentinel.analyzers.semantic import inspect_semantic
from lexsentinel.analyzers.hidden_text import inspect_page
from lexsentinel.analyzers.prompt import detect_prompt, is_academic_context
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
    )


def analyze(path, output_html=None):
    result = Result(
        file_path=path,
        metadata={},
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
        for page_num, page in enumerate(doc, start=1):
            inspect_page(result, page, page_num)

            blocks = page.get_text("dict").get("blocks", [])

            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()

                        if not text:
                            continue

                        marker = detect_prompt(text)

                        if marker:
                            bbox = span.get("bbox")

                            if is_academic_context(text):
                                add_finding(
                                    result,
                                    Finding(
                                        "semantic",
                                        "INFO",
                                        0,
                                        "HIGH",
                                        "Contexto acadêmico detectado",
                                        text[:150],
                                        page_num,
                                        bbox=bbox,
                                    ),
                                )
                            else:
                                add_finding(
                                    result,
                                    Finding(
                                        "prompt_injection",
                                        "CRITICAL",
                                        100,
                                        "HIGH",
                                        "Prompt injection potencial",
                                        text[:150],
                                        page_num,
                                        bbox=bbox,
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
