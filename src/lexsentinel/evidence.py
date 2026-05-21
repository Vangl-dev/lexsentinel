from pathlib import Path
import fitz


def ensure_evidence_dir(output_html: str):
    base = Path(output_html).parent
    evid = base / "evidencias"
    evid.mkdir(parents=True, exist_ok=True)
    return evid


def generate_evidence_image(pdf_path, finding, output_html, index):
    if not finding.page or not finding.bbox:
        return None

    evid_dir = ensure_evidence_dir(output_html)

    doc = fitz.open(pdf_path)
    page = doc[finding.page - 1]

    rect = fitz.Rect(finding.bbox)

    page.draw_rect(
        rect,
        color=(1, 0, 0),
        width=3,
    )

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

    filename = (
        f"pagina_{finding.page:02d}_"
        f"{finding.category}_{index}.png"
    )

    out = evid_dir / filename
    pix.save(str(out))

    return str(out)
