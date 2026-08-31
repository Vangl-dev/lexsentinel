import pikepdf

from lexsentinel.models import Result
from lexsentinel.analyzers.structure import inspect_structure


def create_structure_pdf(path):
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page()

    pdf.Root["/OpenAction"] = pikepdf.Name("/Print")
    pdf.Root["/Metadata"] = pikepdf.Stream(pdf, b"<xmp>test</xmp>")
    pdf.Root["/OCProperties"] = pikepdf.Dictionary()

    names = pikepdf.Dictionary()
    names["/JavaScript"] = pikepdf.Dictionary()
    names["/EmbeddedFiles"] = pikepdf.Dictionary()

    pdf.Root["/Names"] = names

    pdf.save(path)
    pdf.close()


def create_embedded_only_pdf(path):
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page()

    names = pikepdf.Dictionary()
    names["/EmbeddedFiles"] = pikepdf.Dictionary()
    pdf.Root["/Names"] = names

    pdf.save(path)
    pdf.close()


def test_structure_detection(tmp_path):
    pdf_path = tmp_path / "structure.pdf"

    create_structure_pdf(str(pdf_path))

    result = Result(
        file_path=str(pdf_path),
        metadata={},
    )

    inspect_structure(result, str(pdf_path))

    titles = [f.title for f in result.findings]

    assert "OpenAction detectado" in titles
    assert "XMP metadata presente" in titles
    assert "Optional Content Groups" in titles
    assert "JavaScript detectado" in titles
    assert "EmbeddedFiles detectado" in titles

    assert result.total_score > 0


def test_embedded_files_no_high_severity(tmp_path):
    pdf_path = tmp_path / "embedded_only.pdf"

    create_embedded_only_pdf(str(pdf_path))

    result = Result(
        file_path=str(pdf_path),
        metadata={},
    )

    inspect_structure(result, str(pdf_path))

    embedded_finding = None
    for f in result.findings:
        if f.title == "EmbeddedFiles detectado":
            embedded_finding = f
            break

    assert embedded_finding is not None
    assert embedded_finding.severity == "INFO"
    assert embedded_finding.score == 0


def test_embedded_files_reported(tmp_path):
    pdf_path = tmp_path / "embedded_only.pdf"

    create_embedded_only_pdf(str(pdf_path))

    result = Result(
        file_path=str(pdf_path),
        metadata={},
    )

    inspect_structure(result, str(pdf_path))

    titles = [f.title for f in result.findings]
    assert "EmbeddedFiles detectado" in titles


def test_active_vectors_retain_severity(tmp_path):
    pdf_path = tmp_path / "structure.pdf"

    create_structure_pdf(str(pdf_path))

    result = Result(
        file_path=str(pdf_path),
        metadata={},
    )

    inspect_structure(result, str(pdf_path))

    for f in result.findings:
        if f.title == "OpenAction detectado":
            assert f.severity == "HIGH"
            assert f.score == 40
        elif f.title == "JavaScript detectado":
            assert f.severity == "HIGH"
            assert f.score == 70
        elif f.title == "Optional Content Groups":
            assert f.severity == "HIGH"
            assert f.score == 60