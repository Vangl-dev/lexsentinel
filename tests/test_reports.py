from pathlib import Path

from lexsentinel.models import Result, Fingerprint
from lexsentinel.reports.html import render
from lexsentinel.reports.json import render_json


def sample_result():
    fp = Fingerprint(
        filename="teste.pdf",
        file_size=12345,
        sha256="abc123",
        pdf_version="1.7",
        creator="Unit Test",
        producer="PyTest",
        creation_date="2026-01-01",
        mod_date="2026-01-02",
        encrypted=False,
        linearized=True,
    )

    return Result(
        file_path="/tmp/teste.pdf",
        metadata={"Author": "Vanessa"},
        fingerprint=fp,
    )


def test_render_html(tmp_path):
    result = sample_result()
    output = tmp_path / "report.html"

    render(result, str(output))

    assert output.exists()

    content = output.read_text(encoding="utf-8")

    assert "LexSentinel" in content
    assert "teste.pdf" in content
    assert "Fingerprint documental" in content


def test_render_json(tmp_path):
    result = sample_result()
    output = tmp_path / "report.json"

    render_json(result, str(output))

    assert output.exists()

    content = output.read_text(encoding="utf-8")

    assert "abc123" in content
    assert "SAFE" in content