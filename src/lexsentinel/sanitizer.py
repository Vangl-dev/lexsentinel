from pathlib import Path
import fitz
import pikepdf
from pikepdf import Name


DANGEROUS_ACTION_TYPES = {
    Name("/Launch"),
    Name("/ImportData"),
    Name("/JavaScript"),
    Name("/SubmitForm"),
    Name("/RichMediaExecute"),
}

DANGEROUS_ANNOT_SUBTYPES = {
    Name("/Sound"),
    Name("/Movie"),
    Name("/RichMedia"),
}


def _is_action(obj):
    try:
        return isinstance(obj, pikepdf.Dictionary) and "/S" in obj
    except Exception:
        return False


def _is_dangerous_action(obj):
    try:
        return _is_action(obj) and obj["/S"] in DANGEROUS_ACTION_TYPES
    except Exception:
        return False


def _sanitize_action_dict(action_dict, removed, label):
    if action_dict is None:
        return
    try:
        if _is_dangerous_action(action_dict):
            s_val = str(action_dict["/S"])
            removed.append(f"{label} ({s_val})")
            return True
    except Exception:
        pass
    return False


def _sanitize_action_in_obj(obj, key, removed, label):
    try:
        if key in obj:
            action = obj[key]
            if _sanitize_action_dict(action, removed, label):
                del obj[key]
    except Exception:
        pass


def _sanitize_aa_dict(aa, removed, label):
    if aa is None:
        return
    try:
        for key in list(aa.keys()):
            try:
                action = aa[key]
                if _is_dangerous_action(action):
                    s_val = str(action["/S"])
                    removed.append(f"{label} ({s_val})")
                    del aa[key]
            except Exception:
                pass
    except Exception:
        pass


def _sanitize_annotation(annot, removed):
    try:
        if "/Subtype" in annot:
            subtype = annot["/Subtype"]
            if subtype in DANGEROUS_ANNOT_SUBTYPES:
                subtype_str = str(subtype)
                removed.append(f"Annotation {subtype_str}")
                return True

        if "/AA" in annot:
            _sanitize_aa_dict(annot["/AA"], removed, "Annotation AA")

        if _is_dangerous_action(annot):
            s_val = str(annot["/S"])
            removed.append(f"Action annotation ({s_val})")
            return True
    except Exception:
        pass
    return False


def _sanitize_page(page, removed):
    try:
        if "/AA" in page:
            _sanitize_aa_dict(page["/AA"], removed, "Page AA")
            if "/AA" in page and not page["/AA"]:
                del page["/AA"]

        if "/Annots" in page:
            annots = page["/Annots"]
            to_remove = []
            for i, annot_ref in enumerate(annots):
                try:
                    annot = annot_ref
                    if _sanitize_annotation(annot, removed):
                        to_remove.append(i)
                except Exception:
                    pass
            for i in reversed(to_remove):
                try:
                    del annots[i]
                except Exception:
                    pass
            if len(annots) == 0:
                del page["/Annots"]
    except Exception:
        pass


def _sanitize_names(names, removed):
    if names is None:
        return
    try:
        if "/JavaScript" in names:
            js = names["/JavaScript"]
            if isinstance(js, pikepdf.Dictionary):
                if "/Names" in js:
                    del names["/JavaScript"]
                    removed.append("JavaScript (name tree)")
                else:
                    del names["/JavaScript"]
                    removed.append("JavaScript")
            else:
                del names["/JavaScript"]
                removed.append("JavaScript")

        if "/EmbeddedFiles" in names:
            ef = names["/EmbeddedFiles"]
            if isinstance(ef, pikepdf.Dictionary):
                if "/Names" in ef:
                    del names["/EmbeddedFiles"]
                    removed.append("Embedded Files (name tree)")
                else:
                    del names["/EmbeddedFiles"]
                    removed.append("Embedded Files")
            else:
                del names["/EmbeddedFiles"]
                removed.append("Embedded Files")
    except Exception:
        pass


def structural_sanitize(input_path: str, output_path: str):
    removed = []

    pdf = pikepdf.open(input_path)
    root = pdf.Root

    if "/OpenAction" in root:
        _sanitize_action_dict(root["/OpenAction"], removed, "OpenAction")
        if "/OpenAction" in root:
            del root["/OpenAction"]

    if "/AA" in root:
        _sanitize_aa_dict(root["/AA"], removed, "Document AA")
        if "/AA" in root and not root["/AA"]:
            del root["/AA"]

    if "/Metadata" in root:
        del root["/Metadata"]
        removed.append("Metadata")

    if "/OCProperties" in root:
        del root["/OCProperties"]
        removed.append("Hidden Layers")

    if "/AcroForm" in root:
        del root["/AcroForm"]
        removed.append("AcroForm")

    if "/Names" in root:
        _sanitize_names(root["/Names"], removed)

    for page in pdf.pages:
        _sanitize_page(page, removed)

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
