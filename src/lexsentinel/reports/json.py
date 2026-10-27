import json
from pathlib import Path
from dataclasses import asdict

from lexsentinel import __version__


def render_json(result, output_path):
    data = {
        "lexsentinel_version": __version__,
        "analyzed_at": result.analyzed_at,
        "file_path": result.file_path,
        "metadata": result.metadata,
        "fingerprint": asdict(result.fingerprint) if result.fingerprint else None,
        "total_score": result.total_score,
        "risk": result.risk,
        "errors": result.errors,
        "findings": [asdict(f) for f in result.findings],
    }

    Path(output_path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
