"""Build the Academy review DOCX from its Markdown, without extra packages."""
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
ROOT = Path(__file__).resolve().parents[1]


def text(value):
    return escape(re.sub(r"[*`]", "", value))


def paragraph(value="", style=None, size=None, bold=False, color=None):
    props = '<w:pPr>' + (f'<w:pStyle w:val="{style}"/>' if style else "")
    props += '<w:spacing w:after="100"/></w:pPr>'
    run = '<w:rPr>'
    if size:
        run += f'<w:sz w:val="{size}"/>'
    if bold:
        run += "<w:b/>"
    if color:
        run += f'<w:color w:val="{color}"/>'
    run += "</w:rPr>"
    chunks = value.split("<br>")
    body = "<w:br/>".join(f'<w:t xml:space="preserve">{text(c)}</w:t>' for c in chunks)
    return f"<w:p>{props}<w:r>{run}{body}</w:r></w:p>"


def table(rows):
    count = len(rows[0])
    # A4 landscape: 10.49 inches of usable width, 15,100 twips.
    total = 15100
    weights = {
        3: [1.6, 3.4, 5],
        4: [1.1, 2.6, 3.1, 3.7],
        5: [1.4, 2.3, 3.2, 3.3, 1.9],
        6: [1.0, 1.6, 2.8, 3.0, 2.4, 1.4],
    }.get(count, [1] * count)
    if "Effort" in rows[0]:
        weights = [0.8, 2.2, 4.6, 0.65, 2.2]
    elif rows[0][-1] == "Assessment":
        weights = [1.5, 3.1, 4.4, 1.5]
    elif rows[0][-1] == "Tracking":
        weights = [0.8, 4.1, 4.1, 1.5]
    widths = [round(total * weight / sum(weights)) for weight in weights]
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    body = ""
    for index, row in enumerate(rows):
        properties = '<w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if index == 0 else "") + "</w:trPr>"
        cells = ""
        for value, width in zip(row, widths):
            background = "24364B" if index == 0 else ("EEF6F4" if index % 2 else "FFFFFF")
            cells += (
                f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>'
                f'<w:shd w:fill="{background}"/><w:vAlign w:val="top"/></w:tcPr>'
                + paragraph(value, size=20, bold=index == 0, color="FFFFFF" if index == 0 else "24364B")
                + "</w:tc>"
            )
        body += "<w:tr>" + properties + cells + "</w:tr>"
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="15100" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/><w:tblCellMar>'
        '<w:top w:w="100" w:type="dxa"/><w:left w:w="110" w:type="dxa"/>'
        '<w:bottom w:w="100" w:type="dxa"/><w:right w:w="110" w:type="dxa"/>'
        '</w:tblCellMar><w:tblBorders><w:bottom w:val="single" w:sz="4" w:color="D5E3E5"/>'
        '</w:tblBorders></w:tblPr><w:tblGrid>' + grid + "</w:tblGrid>" + body + "</w:tbl>"
    ) + paragraph()


def build(source, target):
    media = {}
    relationships = [
        '<Relationship Id="rIdStyles" Type="' + R + '/styles" Target="styles.xml"/>',
        '<Relationship Id="rIdFooter" Type="' + R + '/footer" Target="footer1.xml"/>',
    ]
    content, lines, i = [], source.read_text().splitlines(), 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in cells):
                    rows.append(cells)
                i += 1
            assert all(len(row) == len(rows[0]) for row in rows), "Inconsistent table columns"
            content.append(table(rows))
            continue
        image = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
        if image:
            caption, filename = image.groups()
            path = ROOT / filename
            with Image.open(path) as im:
                pxw, pxh = im.size
            width = min(8.5, 6.0 * pxw / pxh)
            cx, cy = round(width * 914400), round(width * pxh / pxw * 914400)
            number = len(media) + 1
            name = f"evidence-{number}{path.suffix.lower()}"
            media[name] = path.read_bytes()
            rid = f"rIdImage{number}"
            relationships.append(f'<Relationship Id="{rid}" Type="{R}/image" Target="media/{name}"/>')
            content.append(
                '<w:p><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
                f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{number}" name="Synthetic evidence {number}" descr="{escape(caption)}"/>'
                '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                '<pic:nvPicPr><pic:cNvPr id="0" name="evidence"/><pic:cNvPicPr/></pic:nvPicPr>'
                f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
                '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
                '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
            )
            content.append(paragraph(caption, size=19, color="526A78"))
        elif line == "---":
            content.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        elif line.startswith("# "):
            content.append(paragraph(line[2:], "Title"))
        elif line.startswith("## "):
            content.append(paragraph(line[3:], "Heading1"))
        elif line.startswith("### "):
            content.append(paragraph(line[4:], "Heading2"))
        elif line:
            content.append(paragraph(("• " + line[2:]) if line.startswith("- ") else line))
        i += 1
    section = (
        '<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/>'
        '<w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
        '<w:pgMar w:top="760" w:right="869" w:bottom="760" w:left="869" w:header="360" w:footer="360"/>'
        '</w:sectPr>'
    )
    document = f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>' + "".join(content) + section + "</w:body></w:document>"
    styles = f'''<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="{W}">
    <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:color w:val="24364B"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="260" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
    <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
    <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:keepNext/><w:spacing w:before="150" w:after="240"/></w:pPr><w:rPr><w:b/><w:sz w:val="52"/><w:color w:val="24364B"/></w:rPr></w:style>
    <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:outlineLvl w:val="0"/><w:spacing w:before="250" w:after="130"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="2A6C87"/></w:rPr></w:style>
    <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="25"/></w:rPr></w:style>
    </w:styles>'''
    footer = f'<w:ftr xmlns:w="{W}">' + paragraph("AJ’s Academy • Synthetic-data usability review", size=18) + '<w:p><w:r><w:t>Page </w:t></w:r><w:fldSimple w:instr="PAGE"/></w:p></w:ftr>'
    types = '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Default Extension="png" ContentType="image/png"/><Default Extension="jpg" ContentType="image/jpeg"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
    <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
    <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
    <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>'''
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    core = f'''<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>AJ’s Academy: Holistic Usability Review</dc:title><dc:creator>Replit Agent</dc:creator><dc:description>Synthetic-data review, prioritized backlog and potential bugs</dc:description><dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created></cp:coreProperties>'''
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", f'<Relationships xmlns="{REL}"><Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/><Relationship Id="rIdCore" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>')
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/footer1.xml", footer)
        z.writestr("word/_rels/document.xml.rels", f'<Relationships xmlns="{REL}">' + "".join(relationships) + "</Relationships>")
        z.writestr("docProps/core.xml", core)
        for name, raw in media.items():
            z.writestr("word/media/" + name, raw)
    print(f"Created {target}: {len(media)} evidence images")


if __name__ == "__main__":
    build(ROOT / sys.argv[1], ROOT / sys.argv[2])
