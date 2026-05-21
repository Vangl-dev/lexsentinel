from pathlib import Path
import pikepdf


def sanitize_pdf(input_path: str, output_path: str):
    removed = []

    pdf = pikepdf.open(input_path)
    root = pdf.Root

    # OpenAction
    if "/OpenAction" in root:
        del root["/OpenAction"]
        removed.append("OpenAction")

    # Additional Actions
    if "/AA" in root:
        del root["/AA"]
        removed.append("Additional Actions")

    # Metadata
    if "/Metadata" in root:
        del root["/Metadata"]
        removed.append("Metadata")

    # Optional content groups / hidden layers
    if "/OCProperties" in root:
        del root["/OCProperties"]
        removed.append("OCProperties / Hidden Layers")

    # Names dictionary
    if "/Names" in root:
        names = root["/Names"]

        if "/JavaScript" in names:
            del names["/JavaScript"]
            removed.append("JavaScript Namespace")

        if "/EmbeddedFiles" in names:
            del names["/EmbeddedFiles"]
            removed.append("Embedded Files")

    # annotations
    for page in pdf.pages:
        if "/Annots" not in page:
            continue

        keep = []

        for annot in page["/Annots"]:
            flags = str(annot)

            if (
                "/Hidden" in flags
                or "/Invisible" in flags
                or "/NoView" in flags
            ):
                removed.append("Hidden Annotation")
                continue

            if "/AA" in flags:
                removed.append("Annotation Additional Action")
                continue

            if "/JS" in flags:
                removed.append("Annotation JavaScript")
                continue

            keep.append(annot)

        page["/Annots"] = keep

    pdf.save(output_path)
    pdf.close()

    return sorted(set(removed))
