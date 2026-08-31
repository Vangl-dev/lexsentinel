import pikepdf
from pathlib import Path

from lexsentinel.batch import analyze_batch


def _create_test_pdf(path):
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page()
    pdf.save(str(path))
    pdf.close()


def _create_malformed_pdf(path):
    path.write_bytes(b"%PDF-1.4 invalid content")


def test_batch_multiple_valid(tmp_path):
    pdf1 = tmp_path / "test1.pdf"
    pdf2 = tmp_path / "test2.pdf"
    _create_test_pdf(pdf1)
    _create_test_pdf(pdf2)

    result = analyze_batch([str(pdf1), str(pdf2)])

    assert result["total"] == 2
    assert result["successful"] == 2
    assert result["failed"] == 0
    assert len(result["results"]) == 2


def test_batch_invalid_pdf(tmp_path):
    bad_pdf = tmp_path / "bad.pdf"
    _create_malformed_pdf(bad_pdf)

    result = analyze_batch([str(bad_pdf)])

    assert result["total"] == 1
    assert result["successful"] == 1
    assert len(result["results"][0]["errors"]) > 0


def test_batch_non_pdf_file(tmp_path):
    txt_file = tmp_path / "not_a_pdf.txt"
    txt_file.write_text("hello")

    result = analyze_batch([str(txt_file)])

    assert result["total"] == 1
    assert result["successful"] == 1


def test_batch_directory(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf2 = tmp_path / "b.pdf"
    _create_test_pdf(pdf1)
    _create_test_pdf(pdf2)

    result = analyze_batch([str(tmp_path)])

    assert result["total"] == 2
    assert result["successful"] == 2


def test_batch_empty_directory(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = analyze_batch([str(empty_dir)])

    assert result["total"] == 0
    assert result["successful"] == 0


def test_batch_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    pdf1 = tmp_path / "top.pdf"
    pdf2 = sub / "nested.pdf"
    _create_test_pdf(pdf1)
    _create_test_pdf(pdf2)

    result = analyze_batch([str(tmp_path)], recursive=True)

    assert result["total"] == 2
    assert result["successful"] == 2


def test_batch_non_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    pdf1 = tmp_path / "top.pdf"
    pdf2 = sub / "nested.pdf"
    _create_test_pdf(pdf1)
    _create_test_pdf(pdf2)

    result = analyze_batch([str(tmp_path)], recursive=False)

    assert result["total"] == 1
    assert result["successful"] == 1


def test_batch_output_dir(tmp_path):
    pdf1 = tmp_path / "test.pdf"
    _create_test_pdf(pdf1)

    out_dir = tmp_path / "results"
    result = analyze_batch([str(pdf1)], output_dir=str(out_dir))

    assert result["total"] == 1
    assert result["successful"] == 1
    assert "json_output" in result["results"][0]
    assert Path(result["results"][0]["json_output"]).exists()


def test_batch_results_structure(tmp_path):
    pdf = tmp_path / "test.pdf"
    _create_test_pdf(pdf)

    result = analyze_batch([str(pdf)])

    r = result["results"][0]
    assert "file_path" in r
    assert "success" in r
    assert "fingerprint" in r
    assert "total_score" in r
    assert "risk" in r
    assert "findings_count" in r
    assert "errors" in r
    assert "elapsed_seconds" in r


def test_batch_path_not_found():
    result = analyze_batch(["/nonexistent/path.pdf"])

    assert result["total"] == 1
    assert result["failed"] == 1
    assert "not found" in result["results"][0]["error"].lower()


def test_batch_mixed(tmp_path):
    good = tmp_path / "good.pdf"
    bad = tmp_path / "bad.pdf"
    _create_test_pdf(good)
    _create_malformed_pdf(bad)

    result = analyze_batch([str(good), str(bad)])

    assert result["total"] == 2
    assert result["successful"] == 2
    assert len(result["results"][1]["errors"]) > 0
