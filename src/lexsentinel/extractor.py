import fitz


def extract_raw_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)

    chunks = []

    for i, page in enumerate(doc, start=1):
        text = page.get_text().strip()

        if not text:
            continue

        chunks.append(f"===== PÁGINA {i} =====\n{text}")

    doc.close()

    return "\n\n".join(chunks)
