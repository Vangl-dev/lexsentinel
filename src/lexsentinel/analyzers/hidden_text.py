from lexsentinel.models import Finding
from lexsentinel.analyzers.scoring import add_finding

SHORT_LAYOUT_WORDS = {
    "descrição",
    "resultado",
    "vetor",
    "veredicto",
}


def inspect_page(result, page, page_num):
    blocks = page.get_text("dict").get("blocks", [])

    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()

                if not text:
                    continue

                lowered = text.lower()
                color = span.get("color", 0)
                size = span.get("size", 10)
                bbox = span.get("bbox")

                if color == 16777215:
                    if len(lowered) < 12 or lowered in SHORT_LAYOUT_WORDS:
                        continue

                    score = 5
                    confidence = "LOW"

                    if size < 1:
                        score = 25
                        confidence = "HIGH"

                    add_finding(
                        result,
                        Finding(
                            category="hidden_text",
                            severity="MEDIUM",
                            score=score,
                            confidence=confidence,
                            title="Texto branco suspeito",
                            details=text[:150],
                            page=page_num,
                            bbox=bbox,
                        ),
                    )
