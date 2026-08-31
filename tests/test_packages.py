from unittest.mock import patch, MagicMock

from lexsentinel.packages import (
    check_packages,
    format_check_results,
    PackageInfo,
    _get_installed_version,
    _check_pip_audit,
    _version_satisfies,
    _parse_requirement,
)


def test_check_packages_returns_list():
    results = check_packages(["typer"])
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].name == "typer"


def test_check_packages_installed():
    results = check_packages(["typer"])
    pkg = results[0]
    assert pkg.installed_version != "not installed"
    assert pkg.status == "ok"


def test_check_packages_missing():
    results = check_packages(["nonexistent_package_xyz"])
    pkg = results[0]
    assert pkg.installed_version == "not installed"
    assert pkg.status == "missing"


def test_check_packages_all_deps():
    results = check_packages()
    assert len(results) >= 5
    names = [r.name for r in results]
    assert "typer" in names
    assert "pymupdf" in names
    assert "pikepdf" in names


def test_format_check_results():
    results = [
        PackageInfo(name="test", installed_version="1.0.0", status="ok"),
    ]
    output = format_check_results(results)
    assert "test: 1.0.0" in output


def test_format_check_results_missing():
    results = [
        PackageInfo(name="test", installed_version="not installed", status="missing"),
    ]
    output = format_check_results(results)
    assert "NOT INSTALLED" in output


def test_format_check_results_vulnerable():
    results = [
        PackageInfo(
            name="test",
            installed_version="1.0.0",
            vulnerabilities=["CVE-2024-1234"],
            status="vulnerable",
        ),
    ]
    output = format_check_results(results)
    assert "VULNERABLE" in output
    assert "CVE-2024-1234" in output


def test_get_installed_version():
    ver = _get_installed_version("typer")
    assert ver is not None
    assert isinstance(ver, str)


def test_get_installed_version_missing():
    ver = _get_installed_version("nonexistent_package_xyz")
    assert ver is None


@patch("lexsentinel.packages.subprocess.run")
def test_check_pip_audit_not_installed(mock_run):
    mock_run.side_effect = FileNotFoundError
    result = _check_pip_audit()
    assert "error" in result
    assert "not installed" in result["error"]


@patch("lexsentinel.packages.subprocess.run")
def test_check_pip_audit_timeout(mock_run):
    import subprocess
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="pip-audit", timeout=30)
    result = _check_pip_audit()
    assert "error" in result
    assert "timed out" in result["error"]


@patch("lexsentinel.packages.subprocess.run")
def test_check_pip_audit_invalid_json(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="not json")
    result = _check_pip_audit()
    assert "error" in result
    assert "invalid" in result["error"]


@patch("lexsentinel.packages.subprocess.run")
def test_check_pip_audit_success(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"dependencies": [{"name": "test", "vulnerabilities": []}]}',
    )
    result = _check_pip_audit()
    assert "dependencies" in result
    assert len(result["dependencies"]) == 1


def test_version_satisfies_ge():
    assert _version_satisfies("9.5", ">=9.0") is True
    assert _version_satisfies("8.9", ">=9.0") is False


def test_version_satisfies_eq():
    assert _version_satisfies("1.2", "==1.2") is True
    assert _version_satisfies("1.3", "==1.2") is False


def test_version_satisfies_compatible():
    assert _version_satisfies("1.4.2", "~=1.4.0") is True
    assert _version_satisfies("1.4.3", "~=1.4.2") is True
    assert _version_satisfies("1.5.0", "~=1.4.2") is False


def test_version_satisfies_ne():
    assert _version_satisfies("1.1", "!=1.0") is True
    assert _version_satisfies("1.0", "!=1.0") is False


def test_version_satisfies_gt():
    assert _version_satisfies("1.1", ">1.0") is True
    assert _version_satisfies("1.0", ">1.0") is False


def test_version_satisfies_lt():
    assert _version_satisfies("1.5", "<2.0") is True
    assert _version_satisfies("2.0", "<2.0") is False


def test_version_satisfies_le():
    assert _version_satisfies("2.0", "<=2.0") is True
    assert _version_satisfies("2.1", "<=2.0") is False


def test_version_satisfies_no_spec():
    assert _version_satisfies("1.0.0", "") is True
    assert _version_satisfies("1.0.0", None) is True


def test_parse_requirement_ge():
    name, spec = _parse_requirement("pikepdf>=9.0")
    assert name == "pikepdf"
    assert spec == ">=9.0"


def test_parse_requirement_eq():
    name, spec = _parse_requirement("typer==1.2.3")
    assert name == "typer"
    assert spec == "==1.2.3"


def test_parse_requirement_compatible():
    name, spec = _parse_requirement("rich~=10.0")
    assert name == "rich"
    assert spec == "~=10.0"


def test_parse_requirement_no_version():
    name, spec = _parse_requirement("pymupdf")
    assert name == "pymupdf"
    assert spec is None


def test_parse_requirement_normalization():
    name, spec = _parse_requirement("PySide6>=6.0")
    assert name == "pyside6"
    assert spec == ">=6.0"
