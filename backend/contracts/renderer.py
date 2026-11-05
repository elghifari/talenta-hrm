import re
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from docx import Document
from docx.oxml.parser import parse_xml
from docx.text.run import Run
from lxml import etree

from .constants import MAX_DOCUMENT_BYTES

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TOKEN = re.compile(r"\{\{([^{}]*)\}\}")


class InvalidTemplate(Exception):
    pass


def replace_paragraph(paragraph, token_map):
    runs = [r for r in paragraph.iter(W + "r") if next(r.iterancestors(W + "p"), None) is paragraph]
    texts = [Run(r, None).text for r in runs]
    original = "".join(texts)
    matches = list(TOKEN.finditer(original))
    stripped = TOKEN.sub("", original)
    if "{{" in stripped or "}}" in stripped:
        raise InvalidTemplate("Malformed placeholder")
    offsets, offset = [], 0
    for text in texts:
        offsets.append(offset)
        offset += len(text)
    for match in reversed(matches):
        key = match[1]
        if key not in token_map:
            raise InvalidTemplate("Unknown placeholder")
        start = next(
            i
            for i, text in enumerate(texts)
            if offsets[i] <= match.start() < offsets[i] + len(text)
        )
        end = next(
            i for i, text in enumerate(texts) if offsets[i] < match.end() <= offsets[i] + len(text)
        )
        first, last = Run(runs[start], None), Run(runs[end], None)
        prefix = first.text[: match.start() - offsets[start]]
        suffix = last.text[match.end() - offsets[end] :]
        if start == end:
            first.text = prefix + token_map[key] + suffix
        else:
            first.text = prefix + token_map[key]
            for i in range(start + 1, end):
                Run(runs[i], None).text = ""
            last.text = suffix
    return {match[1] for match in matches}, bool(matches)


def render_docx(template_bytes, token_map, expected_tokens):
    if set(token_map) != set(expected_tokens) or len(template_bytes) > MAX_DOCUMENT_BYTES:
        raise InvalidTemplate("Invalid template input")
    try:
        source = ZipFile(BytesIO(template_bytes))
        with source:
            infos = source.infolist()
            names = [info.filename for info in infos]
            if len(set(names)) != len(names) or sum(i.file_size for i in infos) > 32 * 1024 * 1024:
                raise InvalidTemplate("Invalid package size")
            modified, found = {}, set()
            for info in infos:
                name = info.filename
                lowered = name.casefold()
                if any(s in lowered for s in ("vbaproject", "embeddings/", "activex/")):
                    raise InvalidTemplate("Executable package content")
                if name.endswith(".rels") or name == "[Content_Types].xml":
                    data = source.read(name)
                    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
                        raise InvalidTemplate("XML entities not supported")
                    tree = etree.fromstring(
                        data, etree.XMLParser(resolve_entities=False, no_network=True)
                    )
                    for node in tree.iter():
                        if "macroenabled" in node.get("ContentType", "").casefold():
                            raise InvalidTemplate("Macro-enabled template")
                        if node.get("TargetMode") == "External":
                            if not node.get("Type", "").endswith("/hyperlink"):
                                raise InvalidTemplate("External resource not allowed")
                if name.startswith("word/") and name.endswith(".xml"):
                    data = source.read(name)
                    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
                        raise InvalidTemplate("XML entities not supported")
                    tree = parse_xml(data)
                    changed = False
                    for paragraph in tree.iter(W + "p"):
                        keys, edited = replace_paragraph(paragraph, token_map)
                        found.update(keys)
                        changed |= edited
                    if changed:
                        modified[name] = etree.tostring(
                            tree, encoding="UTF-8", xml_declaration=True, standalone=True
                        )
            if found != set(expected_tokens):
                raise InvalidTemplate("Missing original placeholder")
            output = BytesIO()
            with ZipFile(output, "w") as target:
                for info in infos:
                    target.writestr(info, modified.get(info.filename, source.read(info.filename)))
        content = output.getvalue()
        if len(content) > MAX_DOCUMENT_BYTES:
            raise InvalidTemplate("Document too large")
        with ZipFile(BytesIO(content)) as verification:
            if verification.testzip() is not None:
                raise InvalidTemplate("Corrupt document")
        Document(BytesIO(content))
        return content
    except InvalidTemplate:
        raise
    except (BadZipFile, ValueError, KeyError, TypeError, etree.Error, OSError) as exc:
        raise InvalidTemplate("Invalid DOCX template") from exc
