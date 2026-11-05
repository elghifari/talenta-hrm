from io import BytesIO
from zipfile import ZipFile

import pytest
from contracts.renderer import InvalidTemplate, render_docx
from docx import Document


def template(text=None):
    document = Document()
    p = document.add_paragraph()
    if text is None:
        p.add_run("{{na")
        p.add_run("ma}}")
    else:
        p.add_run(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_split_token_replaced_once_and_user_token_text_is_literal():
    result = render_docx(template(), {"nama": "A & B <C> {{nama}}"}, {"nama"})
    assert Document(BytesIO(result)).paragraphs[0].text == "A & B <C> {{nama}}"


@pytest.mark.parametrize("value", ["Line 1\nLine 2 & <xml> 😀", "{{unknown}}", "A\tB"])
def test_multiline_emoji_and_xml_metacharacters(value):
    result = render_docx(template(), {"nama": value}, {"nama"})
    assert Document(BytesIO(result)).paragraphs[0].text == value


def test_nested_table_and_repeated_tokens():
    doc = Document()
    cell = doc.add_table(rows=1, cols=1).cell(0, 0)
    cell.text = "{{nama}} {{nama}}"
    cell.add_table(rows=1, cols=1).cell(0, 0).text = "{{nama}}"
    stream = BytesIO()
    doc.save(stream)
    result = Document(BytesIO(render_docx(stream.getvalue(), {"nama": "Text"}, {"nama"})))
    assert result.tables[0].cell(0, 0).text.startswith("Text Text")
    assert result.tables[0].cell(0, 0).tables[0].cell(0, 0).text == "Text"


@pytest.mark.parametrize("text", ["{{wrong}}", "no token", "{{nama}"])
def test_wrong_or_missing_original_token_rejected(text):
    with pytest.raises(InvalidTemplate):
        render_docx(template(text), {"nama": "text"}, {"nama"})


def test_corrupt_zip_rejected():
    with pytest.raises(InvalidTemplate):
        render_docx(b"invalid", {"nama": "text"}, {"nama"})


def test_external_image_never_resolved():
    source, target = BytesIO(template()), BytesIO()
    with ZipFile(source) as original, ZipFile(target, "w") as output:
        for item in original.infolist():
            data = original.read(item.filename)
            if item.filename == "word/_rels/document.xml.rels":
                data = data.replace(
                    b"</Relationships>",
                    b'<Relationship Id="external" '
                    b'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                    b'relationships/image" '
                    b'TargetMode="External" Target="http://127.0.0.1:1/private"/></Relationships>',
                )
            output.writestr(item, data)
    with pytest.raises(InvalidTemplate):
        render_docx(target.getvalue(), {"nama": "text"}, {"nama"})


def test_header_image_and_footer_bytes_preserved():
    import base64

    doc = Document(BytesIO(template()))
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
    )
    doc.sections[0].header.paragraphs[0].add_run().add_picture(BytesIO(png))
    doc.sections[0].footer.paragraphs[0].text = "Unchanged footer"
    stream = BytesIO()
    doc.save(stream)
    source = stream.getvalue()
    result = render_docx(source, {"nama": "text"}, {"nama"})
    with ZipFile(BytesIO(source)) as before, ZipFile(BytesIO(result)) as after:
        for name in before.namelist():
            if name.startswith("word/media/") or name.startswith("word/footer"):
                assert before.read(name) == after.read(name)


def test_generated_size_bound(monkeypatch):
    import contracts.renderer as renderer

    monkeypatch.setattr(renderer, "MAX_DOCUMENT_BYTES", 100)
    with pytest.raises(InvalidTemplate):
        render_docx(template(), {"nama": "text"}, {"nama"})
