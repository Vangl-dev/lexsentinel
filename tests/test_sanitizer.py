import pikepdf
from pikepdf import Name, Dictionary, Array, Stream

from lexsentinel.sanitizer import sanitize_pdf


def _create_action_pdf(path, action_type, location="openaction"):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page()
    root = pdf.Root

    action = Dictionary({
        "/S": Name(action_type),
    })

    if action_type == "/Launch":
        action["/F"] = Name("/test.exe")
    elif action_type == "/ImportData":
        action["/F"] = Name("/data.fdf")
    elif action_type == "/JavaScript":
        action["/JS"] = Name("/alert(1)")

    if location == "openaction":
        root["/OpenAction"] = action
    elif location == "aa_doc":
        root["/AA"] = Dictionary({"/WC": action})
    elif location == "aa_page":
        page["/AA"] = Dictionary({"/WC": action})
    elif location == "aa_annot":
        annot = Dictionary({
            "/Type": Name("/Annot"),
            "/Subtype": Name("/Widget"),
            "/AA": Dictionary({"/WC": action}),
            "/Rect": Array([0, 0, 100, 100]),
        })
        page["/Annots"] = Array([annot])

    pdf.save(path)
    pdf.close()


def _create_annotation_pdf(path, subtype):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page()

    annot = Dictionary({
        "/Type": Name("/Annot"),
        "/Subtype": Name(subtype),
        "/Rect": Array([0, 0, 100, 100]),
    })

    if subtype == "/Sound":
        annot["/Sound"] = Stream(pdf, b"\x00" * 10)
    elif subtype == "/Movie":
        annot["/Movie"] = Name("/movie")

    page["/Annots"] = Array([annot])

    pdf.save(path)
    pdf.close()


def _create_nested_page_pdf(path):
    pdf = pikepdf.Pdf.new()

    page1 = pdf.add_blank_page()
    page2 = pdf.add_blank_page()

    pdf.save(path)
    pdf.close()

    pdf = pikepdf.open(path, allow_overwriting_input=True)
    kids = pdf.Root["/Pages"]["/Kids"]
    page_obj1 = kids[0]
    page_obj2 = kids[1]

    child_pages = pdf.make_indirect(Dictionary({
        "/Type": Name("/Pages"),
        "/Count": 1,
        "/Kids": Array([page_obj1]),
    }))
    page_obj1["/Parent"] = child_pages

    parent_pages = pdf.make_indirect(Dictionary({
        "/Type": Name("/Pages"),
        "/Count": 2,
        "/Kids": Array([child_pages, page_obj2]),
    }))
    page_obj2["/Parent"] = parent_pages

    pdf.Root["/Pages"] = parent_pages

    pdf.save(path)
    pdf.close()


def _create_page_aa_pdf(path):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page()

    page["/AA"] = Dictionary({
        "/WC": Dictionary({"_S": Name("/JavaScript"), "_JS": Name("/code")}),
    })

    pdf.save(path)
    pdf.close()


def _create_acroform_pdf(path):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page()

    field = Dictionary({
        "/Type": Name("/Annot"),
        "/Subtype": Name("/Widget"),
        "/T": Name("/field1"),
        "/V": Name("/value"),
    })
    page["/Annots"] = Array([field])

    pdf.Root["/AcroForm"] = Dictionary({
        "/Fields": Array([field]),
    })

    pdf.save(path)
    pdf.close()


def _create_names_pdf(path, with_tree=False):
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page()

    if with_tree:
        js_tree = Dictionary({
            "/Names": Array([
                Name("/JS1"),
                Dictionary({
                    "/S": Name("/JavaScript"),
                    "/JS": Name("/malicious"),
                }),
            ])
        })
        ef_tree = Dictionary({
            "/Names": Array([
                Name("/EF1"),
                Dictionary({
                    "/Type": Name("/Filespec"),
                    "/F": Name("/file.exe"),
                }),
            ])
        })
    else:
        js_tree = Name("/JS1")
        ef_tree = Name("/EF1")

    pdf.Root["/Names"] = Dictionary({
        "/JavaScript": js_tree,
        "/EmbeddedFiles": ef_tree,
    })

    pdf.save(path)
    pdf.close()


def _create_content_pdf(path):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page()
    pdf.Root["/OpenAction"] = Dictionary({"_S": Name("/Launch")})
    pdf.save(path)
    pdf.close()


def test_sanitize_removes_openaction(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_action_pdf(str(source), "/Launch", "openaction")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert cleaned.exists()
    assert any("OpenAction" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    assert "/OpenAction" not in pdf.Root
    pdf.close()


def test_sanitize_removes_launch(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_action_pdf(str(source), "/Launch", "openaction")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Launch" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    assert "/OpenAction" not in pdf.Root
    pdf.close()


def test_sanitize_removes_importdata(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_action_pdf(str(source), "/ImportData", "openaction")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("ImportData" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    assert "/OpenAction" not in pdf.Root
    pdf.close()


def test_sanitize_removes_javascript_action(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_action_pdf(str(source), "/JavaScript", "openaction")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("JavaScript" in r for r in removed)


def test_sanitize_removes_document_aa(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_action_pdf(str(source), "/Launch", "aa_doc")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Document AA" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    assert "/AA" not in pdf.Root
    pdf.close()


def test_sanitize_removes_page_aa(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_action_pdf(str(source), "/Launch", "aa_page")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Page AA" in r for r in removed)


def test_sanitize_removes_annot_aa(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_action_pdf(str(source), "/Launch", "aa_annot")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Annotation AA" in r for r in removed)


def test_sanitize_removes_sound_annotation(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_annotation_pdf(str(source), "/Sound")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Sound" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    page = pdf.pages[0]
    assert "/Annots" not in page
    pdf.close()


def test_sanitize_removes_movie_annotation(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_annotation_pdf(str(source), "/Movie")

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Movie" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    page = pdf.pages[0]
    assert "/Annots" not in page
    pdf.close()


def test_sanitize_removes_acroform(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_acroform_pdf(str(source))

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("AcroForm" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    assert "/AcroForm" not in pdf.Root
    pdf.close()


def test_sanitize_removes_javascript_names(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_names_pdf(str(source), with_tree=False)

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("JavaScript" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    if "/Names" in pdf.Root:
        assert "/JavaScript" not in pdf.Root["/Names"]
    pdf.close()


def test_sanitize_removes_embedded_files(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_names_pdf(str(source), with_tree=False)

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Embedded" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    if "/Names" in pdf.Root:
        assert "/EmbeddedFiles" not in pdf.Root["/Names"]
    pdf.close()


def test_sanitize_removes_names_tree(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_names_pdf(str(source), with_tree=True)

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("name tree" in r for r in removed)


def test_sanitize_nested_page_tree(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"
    _create_nested_page_pdf(str(source))

    pdf_in = pikepdf.open(str(source))
    assert len(pdf_in.pages) == 2
    pdf_in.close()

    sanitize_pdf(str(source), str(cleaned))

    pdf_out = pikepdf.open(str(cleaned))
    assert len(pdf_out.pages) == 2
    pdf_out.close()


def test_sanitize_preserves_content(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"

    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page()
    pdf.Root["/OpenAction"] = Dictionary({
        "/S": Name("/Launch"),
        "/F": Name("/test.exe"),
    })
    pdf.save(str(source))
    pdf.close()

    sanitize_pdf(str(source), str(cleaned))

    verify = pikepdf.open(str(cleaned))
    assert len(verify.pages) == 1
    assert "/OpenAction" not in verify.Root
    verify.close()


def test_sanitize_uses_action_type_not_key(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"

    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page()

    action = Dictionary({
        "/S": Name("/Launch"),
        "/F": Name("/test.exe"),
    })
    pdf.Root["/OpenAction"] = action

    pdf.save(str(source))
    pdf.close()

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Launch" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    assert "/OpenAction" not in pdf.Root
    pdf.close()


def test_sanitize_annotation_by_subtype(tmp_path):
    source = tmp_path / "src.pdf"
    cleaned = tmp_path / "out.pdf"

    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page()

    annot = Dictionary({
        "/Type": Name("/Annot"),
        "/Subtype": Name("/Sound"),
        "/Sound": Stream(pdf, b"\x00" * 10),
        "/Rect": Array([0, 0, 100, 100]),
    })
    page["/Annots"] = Array([annot])

    pdf.save(str(source))
    pdf.close()

    removed = sanitize_pdf(str(source), str(cleaned))

    assert any("Sound" in r for r in removed)

    pdf = pikepdf.open(str(cleaned))
    page_out = pdf.pages[0]
    assert "/Annots" not in page_out
    pdf.close()
