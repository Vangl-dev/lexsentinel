import pikepdf
from lexsentinel.models import Finding
from lexsentinel.analyzers.scoring import add_finding


def inspect_semantic(result, path):
    try:
        pdf = pikepdf.open(path)

        raw = str(pdf)

        markers = [
            "/Alt",
            "/ActualText",
            "/TU",
            "/StructTreeRoot",
            "/Hidden",
            "/NoView",
            "/Invisible",
            "/AA",
            "/JS",
        ]

        for marker in markers:
            if marker in raw:
                add_finding(
                    result,
                    Finding(
                        "semantic",
                        "HIGH",
                        50,
                        "MEDIUM",
                        f"Marcador PDF detectado: {marker}",
                        f"Objeto PDF contém {marker}",
                    ),
                )

    except Exception:
        pass
