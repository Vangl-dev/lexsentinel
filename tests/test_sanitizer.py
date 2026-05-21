import pikepdf

from lexsentinel.sanitizer import sanitize_pdf


def create_test_pdf(path):
    pdf = pikepdf.Pdf.new()

    page = pdf.add_blank_page()

    pdf.Root["/OpenAction"] = pikepdf.Name("/Print")

    names = pikepdf.Dictionary()
    names["/JavaScript"] = pikepdf.Dictionary()
    pdf.Root["/Names"] = names

    pdf.save(path)
    pdf.close()


def test_sanitize_removes_vectors(tmp_path):
    source = tmp_path / "infectado.pdf"
    cleaned = tmp_path / "limpo.pdf"

    create_test_pdf(str(source))

    removed = sanitize_pdf(str(source), str(cleaned))

    assert cleaned.exists()
    assert "OpenAction" in removed
    assert "JavaScript Namespace" in removed