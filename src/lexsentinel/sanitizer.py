from pathlib import Path
import fitz
import pikepdf


def structural_sanitize(input_path: str, output_path: str):
    removed = []

    pdf = pikepdf.open(input_path)
    root = pdf.Root

    if "/OpenAction" in root:
        del root["/OpenAction"]
        removed.append("OpenAction")

    if "/AA" in root:
        del root["/AA"]
        removed.append("Additional Actions")

    if "/Metadata" in root:
        del root["/Metadata"]
        removed.append("Metadata")

    if "/OCProperties" in root:
        del root["/OCProperties"]
        removed.append("Hidden Layers")

    if "/Names" in root:
        names = root["/Names"]

        if "/JavaScript" in names:
            del names["/JavaScript"]
            removed.append("JavaScript")

        if "/EmbeddedFiles" in names:
            del names["/EmbeddedFiles"]
            removed.append("Embedded Files")

    pdf.save(output_path)
    pdf.close()

    return sorted(set(removed))


def aggressive_sanitize(input_path: str, output_path: str):
    src = fitz.open(input_path)
    dst = fitz.open()

    for page in src:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        rect = fitz.Rect(0, 0, pix.width, pix.height)

        new_page = dst.new_page(
            width=pix.width,
            height=pix.height,
        )

        new_page.insert_image(rect, pixmap=pix)

    dst.save(output_path)
    dst.close()
    src.close()

    return [
        "Flattened PDF",
        "Hidden text removed",
        "Invisible overlays removed",
        "Scripts/actions neutralized",
    ]


def sanitize_pdf(input_path: str, output_path: str, aggressive=False):
    if aggressive:
        return aggressive_sanitize(input_path, output_path)

    return structural_sanitize(input_path, output_path)