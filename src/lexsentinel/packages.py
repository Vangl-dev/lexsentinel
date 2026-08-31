import importlib.metadata
import subprocess
import sys
import json
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version, InvalidVersion


@dataclass
class PackageInfo:
    name: str
    installed_version: str
    required_version: Optional[str] = None
    latest_version: Optional[str] = None
    vulnerabilities: List[str] = field(default_factory=list)
    status: str = "ok"


def _parse_requirement(req_str: str) -> Tuple[str, Optional[str]]:
    req_str = req_str.strip()
    if not req_str:
        return ("", None)

    for op in ["~=", "!=", ">=", "<=", "==", ">", "<"]:
        if op in req_str:
            parts = req_str.split(op, 1)
            name = parts[0].strip().lower().replace("-", "_")
            version_spec = parts[1].strip()
            if ";" in version_spec:
                version_spec = version_version.split(";")[0].strip()
            return (name, f"{op}{version_spec}")

    name = req_str.split(";")[0].strip().lower().replace("-", "_")
    return (name, None)


def _version_satisfies(installed: str, required_spec: str) -> bool:
    if not required_spec:
        return True

    try:
        spec = SpecifierSet(required_spec)
        ver = Version(installed)
        return ver in spec
    except InvalidSpecifier:
        return True
    except InvalidVersion:
        return installed == required_spec


def _get_required_versions():
    try:
        from importlib.metadata import metadata as pkg_metadata
        meta = pkg_metadata("lexsentinel")
        requires = meta.get_all("Requires-Dist") or []
        required = {}
        for req_str in requires:
            name, version_spec = _parse_requirement(req_str)
            if name and version_spec:
                required[name] = version_spec
        return required
    except Exception:
        return {}


def _get_installed_version(name: str) -> Optional[str]:
    try:
        normalized = name.lower().replace("-", "_")
        return importlib.metadata.version(normalized)
    except importlib.metadata.PackageNotFoundError:
        return None


def _check_pip_audit() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr.strip()}
    except FileNotFoundError:
        return {"error": "pip-audit not installed"}
    except subprocess.TimeoutExpired:
        return {"error": "pip-audit timed out"}
    except json.JSONDecodeError:
        return {"error": "invalid pip-audit output"}
    except Exception as e:
        return {"error": str(e)}


def check_packages(packages=None) -> List[PackageInfo]:
    if packages is None:
        packages = [
            "typer",
            "rich",
            "pymupdf",
            "pikepdf",
            "weasyprint",
            "pyside6",
        ]

    required = _get_required_versions()
    audit_data = _check_pip_audit()

    vuln_map = {}
    if "dependencies" in audit_data:
        for dep in audit_data["dependencies"]:
            name = dep.get("name", "").lower().replace("-", "_")
            vulns = dep.get("vulnerabilities", [])
            if vulns:
                vuln_map[name] = [v.get("id", "unknown") for v in vulns]

    results = []
    for pkg in packages:
        normalized = pkg.lower().replace("-", "_")
        installed = _get_installed_version(pkg)

        if installed is None:
            results.append(PackageInfo(
                name=pkg,
                installed_version="not installed",
                status="missing",
            ))
            continue

        required_spec = required.get(normalized)
        vulns = vuln_map.get(normalized, [])

        if vulns:
            status = "vulnerable"
        elif required_spec and not _version_satisfies(installed, required_spec):
            status = "version_mismatch"
        else:
            status = "ok"

        results.append(PackageInfo(
            name=pkg,
            installed_version=installed,
            required_version=required_spec,
            vulnerabilities=vulns,
            status=status,
        ))

    return results


def format_check_results(results: List[PackageInfo]) -> str:
    lines = []
    for r in results:
        parts = [f"{r.name}: {r.installed_version}"]

        if r.required_version:
            parts.append(f"(required: {r.required_version})")

        if r.vulnerabilities:
            parts.append(f"[VULNERABLE: {', '.join(r.vulnerabilities)}]")

        if r.status == "missing":
            parts.append("[NOT INSTALLED]")

        lines.append(" ".join(parts))

    return "\n".join(lines)
