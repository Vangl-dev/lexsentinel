import json
import time
from pathlib import Path
from dataclasses import asdict
from typing import List, Optional

from lexsentinel.analyzers.core import analyze
from lexsentinel.models import Result


def analyze_batch(
    paths: List[str],
    output_dir: Optional[str] = None,
    recursive: bool = False,
) -> dict:
    results = []
    successful = 0
    failed = 0

    pdf_paths = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_dir():
            if recursive:
                pdf_paths.extend(sorted(path.rglob("*.pdf")))
            else:
                pdf_paths.extend(sorted(path.glob("*.pdf")))
        elif path.is_file():
            pdf_paths.append(path)
        else:
            results.append({
                "file_path": path_str,
                "success": False,
                "error": f"Path not found: {path_str}",
            })
            failed += 1

    for pdf_path in pdf_paths:
        start_time = time.time()

        try:
            result = analyze(str(pdf_path))
            elapsed = time.time() - start_time

            result_dict = {
                "file_path": str(pdf_path),
                "success": True,
                "fingerprint": asdict(result.fingerprint) if result.fingerprint else None,
                "total_score": result.total_score,
                "risk": result.risk,
                "findings_count": len(result.findings),
                "errors": result.errors,
                "elapsed_seconds": round(elapsed, 3),
            }

            if output_dir:
                out_dir = Path(output_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                json_path = out_dir / f"{pdf_path.stem}_result.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "file_path": str(pdf_path),
                            "metadata": result.metadata,
                            "fingerprint": asdict(result.fingerprint) if result.fingerprint else None,
                            "total_score": result.total_score,
                            "risk": result.risk,
                            "errors": result.errors,
                            "findings": [asdict(fd) for fd in result.findings],
                        },
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )
                result_dict["json_output"] = str(json_path)

            results.append(result_dict)
            successful += 1

        except Exception as e:
            elapsed = time.time() - start_time
            results.append({
                "file_path": str(pdf_path),
                "success": False,
                "error": str(e),
                "elapsed_seconds": round(elapsed, 3),
            })
            failed += 1

    return {
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
    }
