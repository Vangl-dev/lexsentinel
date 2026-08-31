import pikepdf
from pikepdf import Name

from lexsentinel.models import Finding
from lexsentinel.analyzers.scoring import add_finding
from lexsentinel.analyzers.prompt import detect_prompt


STRUCTURE_TYPES_WITH_ALT = {
    Name("/Figure"),
    Name("/Formula"),
    Name("/Form"),
}


def _extract_all_alt_recursive(obj, results, visited=None):
    if visited is None:
        visited = set()

    try:
        if isinstance(obj, pikepdf.Dictionary):
            obj_key = obj.objgen if hasattr(obj, "objgen") else id(obj)
            if obj_key in visited:
                return
            visited.add(obj_key)

            if "/Alt" in obj:
                alt_val = obj["/Alt"]
                if isinstance(alt_val, pikepdf.String):
                    text = str(alt_val).strip()
                    if text:
                        s_value = obj.get("/S")
                        results.append({
                            "text": text,
                            "s_type": s_value,
                        })

            for key in obj:
                try:
                    _extract_all_alt_recursive(obj[key], results, visited)
                except Exception:
                    pass

        elif isinstance(obj, pikepdf.Array):
            for item in obj:
                try:
                    _extract_all_alt_recursive(item, results, visited)
                except Exception:
                    pass
    except Exception:
        pass


def extract_alt_texts(path):
    alt_texts = []
    try:
        pdf = pikepdf.open(path)
        root = pdf.Root

        if "/StructTreeRoot" in root:
            results = []
            _extract_all_alt_recursive(root["/StructTreeRoot"], results)
            for r in results:
                alt_texts.append(r["text"])

        pdf.close()
    except Exception:
        pass

    return alt_texts


def inspect_alt_text(result, path):
    try:
        pdf = pikepdf.open(path)
        root = pdf.Root

        if "/StructTreeRoot" not in root:
            pdf.close()
            return

        entries = []
        _extract_all_alt_recursive(root["/StructTreeRoot"], entries)
        pdf.close()

        for entry in entries:
            text = entry["text"]
            s_type = entry["s_type"]

            marker = detect_prompt(text)

            if marker:
                add_finding(
                    result,
                    Finding(
                        "prompt_injection",
                        "CRITICAL",
                        100,
                        "HIGH",
                        "Prompt injection em alt-text",
                        text[:150],
                    ),
                )
            elif s_type in STRUCTURE_TYPES_WITH_ALT:
                add_finding(
                    result,
                    Finding(
                        "alt_text",
                        "INFO",
                        0,
                        "MEDIUM",
                        "Alt-text de imagem detectado",
                        text[:150],
                    ),
                )
    except Exception:
        pass
