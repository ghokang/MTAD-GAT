"""의존성 없는 최소 OOXML(.docx) 작성기 — 제목/본문/그림/표/각주 없는 학위논문 조판용.

python-docx 등 외부 패키지 없이 표준 라이브러리만으로 Word 문서를 생성한다.
지원: 제목 계층(1~3), 본문 단락, 중앙정렬 그림+캡션, 표, 페이지 나눔, 참고문헌(내어쓰기).
"""
from __future__ import annotations

import struct
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

EMU_PER_INCH = 914400
KO_FONT = "바탕"                 # 한글 본문 (학위논문 관례: 명조 계열)
KO_FONT_HEAD = "맑은 고딕"        # 한글 제목 (고딕 계열)
EN_FONT = "Times New Roman"     # 영문 본문
EN_FONT_HEAD = "Arial"          # 영문 제목

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')


def png_size(path: Path) -> tuple[int, int]:
    """PIL 없이 PNG 헤더(IHDR)에서 픽셀 크기를 읽는다."""
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"PNG가 아님: {path}")
    return struct.unpack(">II", head[16:24])


class Docx:
    def __init__(self, ko_body=KO_FONT, en_body=EN_FONT):
        self.body: list[str] = []
        self.images: list[tuple[str, bytes]] = []   # (파일명, 바이트)
        self.ko_body, self.en_body = ko_body, en_body
        self._img_id = 0

    # ── 내부 유틸 ────────────────────────────────────────────────────────────
    def _rpr(self, size, bold, italic, color, head_font=False, spacing=None):
        ko = KO_FONT_HEAD if head_font else self.ko_body
        en = EN_FONT_HEAD if head_font else self.en_body
        s = f'<w:rFonts w:ascii="{en}" w:hAnsi="{en}" w:eastAsia="{ko}"/>'
        if bold:
            s += "<w:b/>"
        if italic:
            s += "<w:i/>"
        if color:
            s += f'<w:color w:val="{color}"/>'
        if spacing:
            s += f'<w:spacing w:val="{spacing}"/>'
        return s + f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'

    def _p(self, runs_xml, *, align="both", indent=0, hanging=0, line=360,
           before=0, after=120, keep_next=False, page_break_before=False):
        ppr = ["<w:pageBreakBefore/>"] if page_break_before else []
        if keep_next:
            ppr.append("<w:keepNext/>")
        ppr.append(f'<w:spacing w:line="{line}" w:lineRule="auto" '
                   f'w:before="{before}" w:after="{after}"/>')
        ppr.append(f'<w:jc w:val="{align}"/>')
        if hanging:
            ppr.append(f'<w:ind w:left="{hanging}" w:hanging="{hanging}"/>')
        elif indent:
            ppr.append(f'<w:ind w:firstLine="{indent}"/>')
        self.body.append(f"<w:p><w:pPr>{''.join(ppr)}</w:pPr>{runs_xml}</w:p>")

    def _run(self, text, **kw):
        return (f"<w:r><w:rPr>{self._rpr(**kw)}</w:rPr>"
                f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>')

    # ── 공개 API ────────────────────────────────────────────────────────────
    def title(self, text, sub=None):
        self._p(self._run(text, size=36, bold=True, italic=False, color=None, head_font=True),
                align="center", after=120, line=300)
        if sub:
            self._p(self._run(sub, size=24, bold=False, italic=False, color="404040",
                              head_font=True), align="center", after=480, line=300)

    def heading(self, text, level=1, page_break=False):
        size = {1: 28, 2: 24, 3: 22}[level]
        self._p(self._run(text, size=size, bold=True, italic=False, color=None, head_font=True),
                align="left", before=320 if level == 1 else 240, after=140,
                keep_next=True, page_break_before=page_break, line=300)

    def para(self, text, *, indent=200, size=22, align="both", after=120, italic=False,
             color=None, bold=False):
        self._p(self._run(text, size=size, bold=bold, italic=italic, color=color),
                align=align, indent=indent, after=after)

    def figure(self, img_path, caption_ko, caption_en=None, width_in=6.0):
        """중앙정렬 그림 + 캡션(국문/영문 병기 가능)."""
        img_path = Path(img_path)
        self._img_id += 1
        name = f"image{self._img_id}.png"
        self.images.append((name, img_path.read_bytes()))
        rid = f"rIdImg{self._img_id}"
        px_w, px_h = png_size(img_path)
        cx = int(width_in * EMU_PER_INCH)
        cy = int(cx * px_h / px_w)
        drawing = (
            f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{self._img_id}" name="Figure {self._img_id}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{self._img_id}" name="{name}"/>'
            f"<pic:cNvPicPr/></pic:nvPicPr>"
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            f"</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>")
        self._p(drawing, align="center", indent=0, before=200, after=80, keep_next=True)
        self._p(self._run(caption_ko, size=19, bold=False, italic=False, color=None),
                align="center", indent=0, after=40 if caption_en else 280, line=280)
        if caption_en:
            self._p(self._run(caption_en, size=18, bold=False, italic=True, color="404040"),
                    align="center", indent=0, after=280, line=280)

    def table(self, rows, caption=None, caption_en=None, widths=None, header=True):
        """rows: 2차원 리스트(첫 행이 헤더). widths: 열 너비 비율 리스트."""
        if caption:
            self._p(self._run(caption, size=19, bold=True, italic=False, color=None),
                    align="center", indent=0, before=200, after=60, keep_next=True, line=280)
            if caption_en:
                self._p(self._run(caption_en, size=18, bold=False, italic=True, color="404040"),
                        align="center", indent=0, after=80, keep_next=True, line=280)
        ncol = len(rows[0])
        total = 9000
        widths = widths or [1] * ncol
        w = [int(total * x / sum(widths)) for x in widths]
        grid = "".join(f'<w:gridCol w:w="{x}"/>' for x in w)
        xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/>'
               '<w:jc w:val="center"/><w:tblBorders>'
               + "".join(f'<w:{e} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
                         for e in ("top", "bottom", "insideH"))
               + '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
                 '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
                 '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
                 f"</w:tblBorders></w:tblPr><w:tblGrid>{grid}</w:tblGrid>"]
        for ri, row in enumerate(rows):
            hdr = header and ri == 0
            cells = []
            for ci, cell in enumerate(row):
                run = self._run(str(cell), size=19, bold=hdr, italic=False, color=None)
                al = "left" if ci == 0 and not hdr else "center"
                cells.append(
                    f'<w:tc><w:tcPr><w:tcW w:w="{w[ci]}" w:type="dxa"/>'
                    f'<w:vAlign w:val="center"/>'
                    + ('<w:shd w:val="clear" w:fill="F2F2F2"/>' if hdr else "")
                    + "</w:tcPr>"
                    f'<w:p><w:pPr><w:spacing w:line="240" w:lineRule="auto" '
                    f'w:before="40" w:after="40"/><w:jc w:val="{al}"/></w:pPr>{run}</w:p></w:tc>')
            xml.append(f"<w:tr>{''.join(cells)}</w:tr>")
        xml.append("</w:tbl>")
        self.body.append("".join(xml))
        self._p("", after=200)   # 표 뒤 여백

    def reference(self, text):
        self._p(self._run(text, size=20, bold=False, italic=False, color=None),
                align="left", indent=0, hanging=400, after=80, line=280)

    def page_break(self):
        self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def spacer(self, after=240):
        self._p("", after=after)

    # ── 저장 ────────────────────────────────────────────────────────────────
    def save(self, path):
        img_rels = "".join(
            f'<Relationship Id="rIdImg{i+1}" Type="http://schemas.openxmlformats.org/'
            f'officeDocument/2006/relationships/image" Target="media/{n}"/>'
            for i, (n, _) in enumerate(self.images))
        ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Default Extension="png" ContentType="image/png"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
              'officedocument.wordprocessingml.document.main+xml"/>'
              '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-'
              'officedocument.wordprocessingml.styles+xml"/></Types>')
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
                '2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
                 f'2006/relationships/styles" Target="styles.xml"/>{img_rels}</Relationships>')
        styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                  '<w:docDefaults><w:rPrDefault><w:rPr>'
                  f'<w:rFonts w:ascii="{self.en_body}" w:hAnsi="{self.en_body}" '
                  f'w:eastAsia="{self.ko_body}"/><w:sz w:val="22"/><w:szCs w:val="22"/>'
                  '<w:lang w:val="en-US" w:eastAsia="ko-KR"/></w:rPr></w:rPrDefault>'
                  '<w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/>'
                  "</w:pPr></w:pPrDefault></w:docDefaults>"
                  '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
                  '<w:name w:val="Normal"/><w:qFormat/></w:style></w:styles>')
        doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               f"<w:document {NS}><w:body>{''.join(self.body)}"
               '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
               '<w:pgMar w:top="1701" w:right="1418" w:bottom="1701" w:left="1418" '
               'w:header="851" w:footer="992" w:gutter="0"/></w:sectPr></w:body></w:document>')
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct)
            z.writestr("_rels/.rels", rels)
            z.writestr("word/_rels/document.xml.rels", drels)
            z.writestr("word/styles.xml", styles)
            z.writestr("word/document.xml", doc)
            for name, data in self.images:
                z.writestr(f"word/media/{name}", data)
        return path
