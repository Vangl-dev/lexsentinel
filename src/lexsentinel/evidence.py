from pathlib import Path
import fitz

from lexsentinel.utils import sanitize_filename

CONTEXT_MARGIN = 90


def ensure_evidence_dir(output_html: str):
    base = Path(output_html).parent
    evid = base / "evidencias"
    evid.mkdir(parents=True, exist_ok=True)
    return evid


def generate_evidence_image(pdf_path, finding, output_html, index):
    if not finding.page or not finding.bbox:
        return None

    evid_dir = ensure_evidence_dir(output_html)

    with fitz.open(pdf_path) as doc:
        page = doc[finding.page - 1]

        rect = fitz.Rect(finding.bbox)

        page.draw_rect(
            rect,
            color=(1, 0, 0),
            width=2,
        )

        # Recorta uma faixa da largura da página em volta do achado,
        # para que o trecho fique legível no laudo.
        clip = fitz.Rect(
            page.rect.x0,
            rect.y0 - CONTEXT_MARGIN,
            page.rect.x1,
            rect.y1 + CONTEXT_MARGIN,
        ) & page.rect

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip)

    filename = (
        f"{sanitize_filename(pdf_path)}_"
        f"pagina_{finding.page:02d}_"
        f"{finding.category}_{index}.png"
    )

    out = evid_dir / filename
    pix.save(str(out))

    return str(out)
