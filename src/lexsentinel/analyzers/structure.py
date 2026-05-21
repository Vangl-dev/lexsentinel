import pikepdf
from lexsentinel.models import Finding
from lexsentinel.analyzers.scoring import add_finding


def safe_str(value):
    try:
        return str(value)
    except Exception:
        return "<não serializável>"


def inspect_structure(result, path):
    try:
        pdf = pikepdf.open(path)
        root = pdf.Root

        if "/OpenAction" in root:
            open_action = safe_str(root["/OpenAction"])

            add_finding(
                result,
                Finding(
                    "structure",
                    "HIGH",
                    40,
                    "HIGH",
                    "OpenAction detectado",
                    (
                        "Objeto estrutural PDF '/OpenAction' presente "
                        f"no catálogo raiz. Valor detectado: {open_action}"
                    ),
                ),
            )

        if "/AcroForm" in root:
            acro = safe_str(root["/AcroForm"])

            add_finding(
                result,
                Finding(
                    "structure",
                    "LOW",
                    10,
                    "MEDIUM",
                    "AcroForm presente",
                    (
                        "Formulário interativo detectado no documento. "
                        f"Objeto: {acro}"
                    ),
                ),
            )

        if "/Metadata" in root:
            metadata_obj = safe_str(root["/Metadata"])

            add_finding(
                result,
                Finding(
                    "metadata",
                    "INFO",
                    0,
                    "HIGH",
                    "XMP metadata presente",
                    (
                        "Metadata stream estrutural detectado. "
                        f"Objeto: {metadata_obj}"
                    ),
                ),
            )

        if "/OCProperties" in root:
            ocg = safe_str(root["/OCProperties"])

            add_finding(
                result,
                Finding(
                    "structure",
                    "HIGH",
                    60,
                    "HIGH",
                    "Optional Content Groups",
                    (
                        "Camadas opcionais PDF detectadas "
                        f"(OCG/OCProperties). Objeto: {ocg}"
                    ),
                ),
            )

        if "/Names" in root:
            names = root["/Names"]

            if "/EmbeddedFiles" in names:
                embedded = safe_str(names["/EmbeddedFiles"])

                add_finding(
                    result,
                    Finding(
                        "embedded",
                        "HIGH",
                        50,
                        "HIGH",
                        "EmbeddedFiles detectado",
                        (
                            "Namespace estrutural '/EmbeddedFiles' presente. "
                            f"Objeto: {embedded}"
                        ),
                    ),
                )

            if "/JavaScript" in names:
                js = safe_str(names["/JavaScript"])

                add_finding(
                    result,
                    Finding(
                        "javascript",
                        "HIGH",
                        70,
                        "HIGH",
                        "JavaScript detectado",
                        (
                            "Namespace estrutural '/JavaScript' presente. "
                            f"Objeto: {js}"
                        ),
                    ),
                )

    except Exception as e:
        add_finding(
            result,
            Finding(
                "engine",
                "INFO",
                0,
                "LOW",
                "Erro técnico controlado",
                str(e),
            ),
        )