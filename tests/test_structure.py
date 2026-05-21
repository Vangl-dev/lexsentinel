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