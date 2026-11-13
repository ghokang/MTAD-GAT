"""
=============================================================================
Markdown 리포트 → Word(.docx) 변환기
=============================================================================

full_pipeline_v4*_add.py 가 생성한 리포트(v4*_add_report.md)를 이미지·표를
모두 포함한 보기 좋은 Word 문서로 변환한다. 내용은 원본 md와 동일하며,
읽기 편하도록 서식(제목 스타일, 표 음영·행 줄무늬, 그림 폭 맞춤, 목차,
쪽 번호)만 입힌다.

실행:
    python md_to_docx.py                       # v4*_add_report.md 전부 변환
    python md_to_docx.py v4_k2_add_report.md   # 특정 파일만 변환

의존성:
    pip install python-docx
=============================================================================
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

ROOT = Path(__file__).resolve().parent

# ── 디자인 토큰 ─────────────────────────────────────────────────────────────
FONT_LATIN = "Calibri"
FONT_EAST = "Malgun Gothic"     # 한글: Windows/Office 표준. 없으면 OS가 대체
FONT_MONO = "Consolas"

INK = RGBColor(0x1A, 0x1A, 0x1A)        # 본문
MUTED = RGBColor(0x5A, 0x63, 0x6B)      # 캡션·보조 설명
ACCENT = RGBColor(0x1F, 0x3D, 0x5C)     # 제목 (짙은 남색)
ACCENT2 = RGBColor(0x2E, 0x5E, 0x88)    # 소제목

HDR_FILL = "1F3D5C"     # 표 머리행 배경
BAND_FILL = "F1F4F7"    # 표 줄무늬 배경
CODE_FILL = "F4F6F8"    # 코드블록 배경

PAGE_W, PAGE_H = Cm(21.0), Cm(29.7)             # A4
MARGIN_X, MARGIN_TOP, MARGIN_BOT = Cm(1.8), Cm(1.9), Cm(1.7)
CONTENT_W_CM = 21.0 - 1.8 * 2                   # = 17.4cm
MAX_IMG_H_CM = 20.5                             # 캡션 자리를 남긴 그림 최대 높이


# ─────────────────────────────────────────────────────────────────────────────
# Markdown 파싱
# ─────────────────────────────────────────────────────────────────────────────
def parse_blocks(md: str) -> List[dict]:
    """마크다운 텍스트 → 블록 리스트."""
    lines = md.splitlines()
    blocks: List[dict] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.rstrip()

        if not s.strip():
            i += 1
            continue

        # 수평선 — H2에 밑줄 테두리를 주므로 별도 렌더링하지 않음
        if s.strip() == "---":
            i += 1
            continue

        # 코드 펜스
        if s.startswith("```"):
            i += 1
            body = []
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            blocks.append({"t": "code", "lines": body})
            continue

        # 표 (연속된 | 로 시작하는 줄)
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            blocks.append({"t": "table", "rows": rows})
            continue

        # 제목
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            blocks.append({"t": "h", "level": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue

        # 이미지 (한 줄 전체)
        m = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", s)
        if m:
            blocks.append({"t": "img", "alt": m.group(1), "src": m.group(2)})
            i += 1
            continue

        # 인용구
        if s.startswith(">"):
            body = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                body.append(lines[i].lstrip()[1:].strip())
                i += 1
            blocks.append({"t": "quote", "text": " ".join(body)})
            continue

        # 그림 캡션: *Figure 1. ...*  (단, **bold** 문단은 제외)
        if s.startswith("*") and not s.startswith("**") and s.endswith("*") and len(s) > 2:
            blocks.append({"t": "caption", "text": s[1:-1].strip()})
            i += 1
            continue

        # 중첩 불릿
        m = re.match(r"^\s{2,}[-*]\s+(.*)$", s)
        if m:
            blocks.append({"t": "li", "level": 2, "text": m.group(1).strip()})
            i += 1
            continue

        # 불릿
        m = re.match(r"^[-*]\s+(.*)$", s)
        if m:
            blocks.append({"t": "li", "level": 1, "text": m.group(1).strip()})
            i += 1
            continue

        # 번호 목록 (md에 적힌 번호를 그대로 유지)
        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m:
            blocks.append({"t": "ol", "num": m.group(1), "text": m.group(2).strip()})
            i += 1
            continue

        blocks.append({"t": "p", "text": s.strip()})
        i += 1

    return blocks


def split_inline(text: str) -> List[Tuple[str, str]]:
    """인라인 서식 분해 → [(kind, text)], kind ∈ {plain, bold, code}."""
    out: List[Tuple[str, str]] = []
    for part in re.split(r"(\*\*.+?\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append(("bold", part[2:-2]))
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append(("code", part[1:-1]))
        else:
            out.append(("plain", part))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# docx 저수준 헬퍼
# ─────────────────────────────────────────────────────────────────────────────
def shade(el, fill: str) -> None:
    """셀/문단에 배경색 지정."""
    pr = el.get_or_add_tcPr() if el.tag.endswith("}tc") else el.get_or_add_pPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), fill)
    pr.append(sh)


def para_border(p, *, bottom: Optional[str] = None, box: Optional[str] = None,
                size: int = 6, space: int = 6) -> None:
    """문단에 테두리(밑줄 또는 박스) 추가."""
    pPr = p._p.get_or_add_pPr()
    bd = OxmlElement("w:pBdr")
    sides = [("bottom", bottom)] if bottom else \
            [(s, box) for s in ("top", "left", "bottom", "right")]
    for side, color in sides:
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(size))
        e.set(qn("w:space"), str(space))
        e.set(qn("w:color"), color)
        bd.append(e)
    pPr.append(bd)


def set_cell_margins(table, *, top=60, bottom=60, left=90, right=90) -> None:
    """표 셀 안쪽 여백 (dxa 단위, 1/20 pt)."""
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:w"), str(val))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblPr.append(mar)


def repeat_header(row) -> None:
    """표가 페이지를 넘어갈 때 머리행 반복."""
    trPr = row._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader")
    e.set(qn("w:val"), "true")
    trPr.append(e)


def keep_with_next(p) -> None:
    p.paragraph_format.keep_with_next = True


def style_run(run, *, size: float = 10, bold: bool = False, italic: bool = False,
              color: RGBColor = INK, mono: bool = False) -> None:
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    name = FONT_MONO if mono else FONT_LATIN
    run.font.name = name
    # 한글(동아시아) 글꼴을 별도로 지정해야 Word에서 제대로 적용된다
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rPr.append(rf)
    rf.set(qn("w:ascii"), name)
    rf.set(qn("w:hAnsi"), name)
    rf.set(qn("w:eastAsia"), FONT_MONO if mono else FONT_EAST)


def add_runs(p, text: str, *, size: float = 10, color: RGBColor = INK,
             base_bold: bool = False, italic: bool = False) -> None:
    """인라인 서식(**bold**, `code`)을 반영해 run들을 추가."""
    for kind, chunk in split_inline(text):
        r = p.add_run(chunk)
        if kind == "bold":
            style_run(r, size=size, bold=True, italic=italic, color=color)
        elif kind == "code":
            style_run(r, size=size - 0.5, bold=base_bold, italic=italic,
                      color=RGBColor(0xB0, 0x30, 0x60), mono=True)
        else:
            style_run(r, size=size, bold=base_bold, italic=italic, color=color)


def add_page_number_footer(section) -> None:
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "18")
    rPr.append(sz)
    r.append(rPr)
    fld.append(r)
    p._p.append(fld)


# ─────────────────────────────────────────────────────────────────────────────
# 블록 렌더링
# ─────────────────────────────────────────────────────────────────────────────
NUM_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
CENTER_TOKENS = {"***", "**", "*", "n.s.", "-", "—"}


def cell_alignment(text: str) -> int:
    t = text.strip()
    if t in CENTER_TOKENS:
        return WD_ALIGN_PARAGRAPH.CENTER
    if NUM_RE.match(t.replace(",", "")):
        return WD_ALIGN_PARAGRAPH.RIGHT
    return WD_ALIGN_PARAGRAPH.LEFT


def table_font_size(ncols: int) -> float:
    """열이 많을수록 글자를 줄여 한 페이지 폭에 들어가게 한다."""
    if ncols <= 4:
        return 9.5
    if ncols <= 6:
        return 8.5
    if ncols <= 8:
        return 7.5
    if ncols <= 10:
        return 7.0
    return 6.5


def render_table(doc: Document, rows: List[str]) -> None:
    grid = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    # 두 번째 줄(---|---)은 구분선이므로 제거
    if len(grid) >= 2 and all(set(c) <= set("-: ") and c for c in grid[1]):
        header, body = grid[0], grid[2:]
    else:
        header, body = grid[0], grid[1:]

    ncols = max(len(header), max((len(r) for r in body), default=0))
    header += [""] * (ncols - len(header))
    fs = table_font_size(ncols)

    table = doc.add_table(rows=1, cols=ncols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    set_cell_margins(table)

    # 머리행
    for j, txt in enumerate(header):
        cell = table.rows[0].cells[j]
        shade(cell._tc, HDR_FILL)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        r = p.add_run(re.sub(r"\*\*(.+?)\*\*", r"\1", txt))
        style_run(r, size=fs, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    repeat_header(table.rows[0])

    # 본문 행
    for bi, brow in enumerate(body):
        brow = brow + [""] * (ncols - len(brow))
        cells = table.add_row().cells
        for j, txt in enumerate(brow):
            if bi % 2 == 1:
                shade(cells[j]._tc, BAND_FILL)
            p = cells[j].paragraphs[0]
            p.alignment = cell_alignment(txt)
            p.paragraph_format.space_before = Pt(0.5)
            p.paragraph_format.space_after = Pt(0.5)
            add_runs(p, txt, size=fs)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def render_image(doc: Document, src: str, base_dir: Path) -> bool:
    path = (base_dir / src.lstrip("./")).resolve()
    if not path.exists():
        alt = (base_dir / src).resolve()
        path = alt if alt.exists() else path
    if not path.exists():
        p = doc.add_paragraph()
        add_runs(p, f"[그림 파일을 찾을 수 없음: {src}]", size=9, color=MUTED, italic=True)
        return False

    with Image.open(path) as im:
        w_px, h_px = im.size
    w_cm = CONTENT_W_CM
    h_cm = w_cm * h_px / w_px
    if h_cm > MAX_IMG_H_CM:           # 세로로 긴 그림은 높이 기준으로 축소
        h_cm = MAX_IMG_H_CM
        w_cm = h_cm * w_px / h_px

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    keep_with_next(p)
    p.add_run().add_picture(str(path), width=Cm(w_cm), height=Cm(h_cm))
    return True


def render_blocks(doc: Document, blocks: List[dict], base_dir: Path) -> None:
    for b in blocks:
        t = b["t"]

        if t == "h":
            lvl = b["level"]
            if lvl == 1:
                continue                      # 표지에서 이미 출력함
            p = doc.add_paragraph()
            pf = p.paragraph_format
            if lvl == 2:
                pf.space_before, pf.space_after = Pt(20), Pt(7)
                add_runs(p, b["text"], size=14.5, color=ACCENT, base_bold=True)
                para_border(p, bottom="C3CEDA", size=8, space=4)
            else:
                pf.space_before, pf.space_after = Pt(13), Pt(4)
                add_runs(p, b["text"], size=11.5, color=ACCENT2, base_bold=True)
            pf.keep_with_next = True

        elif t == "p":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf = p.paragraph_format
            pf.space_after, pf.line_spacing = Pt(6), 1.3
            add_runs(p, b["text"])

        elif t == "li":
            p = doc.add_paragraph()
            pf = p.paragraph_format
            lvl = b["level"]
            pf.left_indent = Cm(0.75 * lvl + 0.15)
            pf.first_line_indent = Cm(-0.42)
            pf.space_after, pf.line_spacing = Pt(3), 1.25
            bullet = "•  " if lvl == 1 else "–  "
            style_run(p.add_run(bullet), size=10, color=ACCENT2, bold=True)
            add_runs(p, b["text"])

        elif t == "ol":
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent = Cm(0.85)
            pf.first_line_indent = Cm(-0.85)
            pf.space_after, pf.line_spacing = Pt(6), 1.3
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            style_run(p.add_run(f"{b['num']}.".ljust(4)), size=10, bold=True, color=ACCENT2)
            add_runs(p, b["text"])

        elif t == "caption":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf = p.paragraph_format
            pf.space_before, pf.space_after = Pt(1), Pt(12)
            add_runs(p, b["text"], size=9, color=MUTED, italic=True)

        elif t == "img":
            render_image(doc, b["src"], base_dir)

        elif t == "table":
            render_table(doc, b["rows"])

        elif t == "code":
            tbl = doc.add_table(rows=1, cols=1)
            tbl.style = "Table Grid"
            cell = tbl.rows[0].cells[0]
            shade(cell._tc, CODE_FILL)
            set_cell_margins(tbl, top=100, bottom=100, left=160, right=160)
            cell.paragraphs[0]._p.getparent().remove(cell.paragraphs[0]._p)
            for ln in b["lines"]:
                p = cell.add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.15
                style_run(p.add_run(ln if ln.strip() else " "), size=8.5, mono=True,
                          color=RGBColor(0x24, 0x29, 0x2E))
            doc.add_paragraph().paragraph_format.space_after = Pt(4)

        elif t == "quote":
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent, pf.right_indent = Cm(0.5), Cm(0.5)
            pf.space_before, pf.space_after = Pt(8), Pt(8)
            shade(p._p, "FFF6E0")
            para_border(p, box="E0B341", size=6, space=8)
            add_runs(p, b["text"], size=9.5, color=RGBColor(0x5C, 0x43, 0x0F))


def build_cover(doc: Document, title: str, meta: List[dict], src_name: str) -> None:
    """표지: 제목 + 원본 md의 첫 불릿(메타데이터) 목록."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(26)
    p.paragraph_format.space_after = Pt(2)
    add_runs(p, title, size=21, color=ACCENT, base_bold=True)
    para_border(p, bottom="1F3D5C", size=14, space=8)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(16)
    add_runs(p, f"원본 리포트: {src_name}", size=9, color=MUTED, italic=True)

    for b in meta:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent, pf.first_line_indent = Cm(0.9), Cm(-0.42)
        pf.space_after, pf.line_spacing = Pt(3), 1.25
        style_run(p.add_run("•  "), size=10, color=ACCENT2, bold=True)
        add_runs(p, b["text"])


def build_toc(doc: Document, blocks: List[dict]) -> None:
    """정적 목차 (H2/H3). Word 필드가 아니라 실제 텍스트라 열자마자 보인다."""
    heads = [b for b in blocks if b["t"] == "h" and b["level"] in (2, 3)]
    if len(heads) < 3:
        return
    p = doc.add_paragraph()
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(22), Pt(6)
    add_runs(p, "목차", size=13, color=ACCENT, base_bold=True)
    para_border(p, bottom="C3CEDA", size=8, space=4)
    for h in heads:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.5 if h["level"] == 2 else 1.3)
        pf.space_after, pf.line_spacing = Pt(2), 1.15
        txt = re.sub(r"\*\*(.+?)\*\*", r"\1", h["text"])
        add_runs(p, txt, size=10 if h["level"] == 2 else 9.5,
                 color=INK if h["level"] == 2 else MUTED,
                 base_bold=(h["level"] == 2))


def convert(md_path: Path) -> Path:
    md = md_path.read_text(encoding="utf-8")
    blocks = parse_blocks(md)

    title = next((b["text"] for b in blocks if b["t"] == "h" and b["level"] == 1),
                 md_path.stem)

    # 제목 바로 뒤에 오는 연속 불릿 또는 "**키:** 값" 문단 = 메타데이터 → 표지로 분리
    first_h1 = next(i for i, b in enumerate(blocks) if b["t"] == "h" and b["level"] == 1)
    j = first_h1 + 1
    meta = []
    while j < len(blocks) and (blocks[j]["t"] == "li" or
                               (blocks[j]["t"] == "p" and blocks[j]["text"].startswith("**"))):
        meta.append(blocks[j])
        j += 1
    rest = blocks[j:]

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = PAGE_W, PAGE_H
    sec.left_margin = sec.right_margin = MARGIN_X
    sec.top_margin, sec.bottom_margin = MARGIN_TOP, MARGIN_BOT
    add_page_number_footer(sec)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_LATIN
    normal.font.size = Pt(10)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_EAST)

    build_cover(doc, title, meta, md_path.name)
    build_toc(doc, rest)
    render_blocks(doc, rest, md_path.parent)

    out = md_path.with_suffix(".docx")
    doc.save(out)
    return out


def main() -> None:
    targets = [Path(a) for a in sys.argv[1:]] or sorted(ROOT.glob("v4*_add_report.md"))
    if not targets:
        print("변환할 md 파일이 없습니다.")
        return
    print("=" * 64)
    print("Markdown 리포트 → Word 변환")
    print("=" * 64)
    for md_path in targets:
        md_path = md_path if md_path.is_absolute() else (ROOT / md_path)
        if not md_path.exists():
            print(f"  [건너뜀] 파일 없음: {md_path}")
            continue
        out = convert(md_path)
        n_img = sum(1 for b in parse_blocks(md_path.read_text(encoding='utf-8'))
                    if b["t"] == "img")
        n_tbl = sum(1 for b in parse_blocks(md_path.read_text(encoding='utf-8'))
                    if b["t"] == "table")
        print(f"  {md_path.name:<26s} → {out.name:<28s} "
              f"(그림 {n_img}개, 표 {n_tbl}개, {out.stat().st_size/1e6:.1f} MB)")
    print("완료")


if __name__ == "__main__":
    main()
