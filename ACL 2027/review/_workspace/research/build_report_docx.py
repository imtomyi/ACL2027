#!/usr/bin/env python3
"""Build the systematic scoping review DOCX from a Markdown source.

Design system: narrative_proposal preset + editorial_cover first-page pattern.
Named overrides: 29 pt cover title; 9 pt table body; section headings start on a new
page; compact 1.15 line spacing inside tables. All overrides are applied globally.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "report_draft.md"
OUTDIR = ROOT.parent / "outputs" / "acl2027_scoping_review_20260824"
OUT = OUTDIR / "systematic_scoping_review_llm_qualitative_analysis.docx"
AUDIT = OUTDIR / "docx_design_audit.json"

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
INK = "0B2545"
MUTED = "667085"
LIGHT = "F4F6F9"
GRID = "CBD5E1"
GOLD = "9A6A00"
WHITE = "FFFFFF"


def set_run_font(run, *, size=11, color="000000", bold=None, italic=None, name="Calibri"):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    rep = OxmlElement("w:tblHeader")
    rep.set(qn("w:val"), "true")
    tr_pr.append(rep)


def keep_table_row_together(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    tr_pr.append(cant)


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa):
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        keep_table_row_together(row)
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths_dxa[idx]))
            tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(widths_dxa[idx] / 1440)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            cell_margins(cell)


def apply_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), GRID)


def add_hyperlink(paragraph, text, url, *, bold=False, italic=False, color=BLUE):
    part = paragraph.part
    rel_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    r_fonts = OxmlElement("w:rFonts")
    r_fonts.set(qn("w:ascii"), "Calibri")
    r_fonts.set(qn("w:hAnsi"), "Calibri")
    r_pr.append(r_fonts)
    c = OxmlElement("w:color")
    c.set(qn("w:val"), color)
    r_pr.append(c)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    r_pr.append(u)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "22")
    r_pr.append(sz)
    if bold:
        r_pr.append(OxmlElement("w:b"))
    if italic:
        r_pr.append(OxmlElement("w:i"))
    run.append(r_pr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


INLINE_RE = re.compile(r"(\[[^\]]+\]\(https?://[^)]+\)|\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def add_inline(paragraph, text, *, default_size=11, default_color="000000"):
    pos = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos:match.start()])
            set_run_font(run, size=default_size, color=default_color)
        token = match.group(0)
        link = re.fullmatch(r"\[([^\]]+)\]\((https?://[^)]+)\)", token)
        if link:
            add_hyperlink(paragraph, link.group(1), link.group(2))
        elif token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, size=default_size, color=default_color, bold=True)
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, size=max(default_size - 0.5, 8), color=DARK_BLUE, name="Courier New")
        else:
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, size=default_size, color=default_color, italic=True)
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        set_run_font(run, size=default_size, color=default_color)


def setup_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.space_before = Pt(0)
    pf.space_after = Pt(8)
    pf.line_spacing = 1.333
    for name, size, color, before, after in (
        ("Heading 1", 16, BLUE, 18, 10),
        ("Heading 2", 13, BLUE, 12, 6),
        ("Heading 3", 12, DARK_BLUE, 8, 4),
    ):
        style = doc.styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        sp = style.paragraph_format
        sp.space_before = Pt(before)
        sp.space_after = Pt(after)
        sp.keep_with_next = True
        sp.keep_together = True
        sp.line_spacing = 1.0
    table_cite = doc.styles.add_style("Table Citation", 1)
    table_cite.font.name = "Calibri"
    table_cite._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    table_cite._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    table_cite.font.size = Pt(9)
    table_cite.font.color.rgb = RGBColor.from_string(MUTED)
    table_cite.paragraph_format.space_before = Pt(4)
    table_cite.paragraph_format.space_after = Pt(4)
    table_cite.paragraph_format.line_spacing = 1.0


def add_custom_numbering(doc, bullet=True):
    numbering = doc.part.numbering_part.element
    existing = [int(x.get(qn("w:abstractNumId"))) for x in numbering.findall(qn("w:abstractNum"))]
    abs_id = max(existing, default=0) + 1
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abs_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)
    lvl = OxmlElement("w:lvl")
    lvl.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    lvl.append(start)
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "bullet" if bullet else "decimal")
    lvl.append(num_fmt)
    lvl_text = OxmlElement("w:lvlText")
    lvl_text.set(qn("w:val"), "•" if bullet else "%1.")
    lvl.append(lvl_text)
    lvl_jc = OxmlElement("w:lvlJc")
    lvl_jc.set(qn("w:val"), "left")
    lvl.append(lvl_jc)
    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "540")
    tabs.append(tab)
    p_pr.append(tabs)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "540")
    ind.set(qn("w:hanging"), "280")
    p_pr.append(ind)
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:after"), "80")
    spacing.set(qn("w:line"), "290")
    spacing.set(qn("w:lineRule"), "auto")
    p_pr.append(spacing)
    lvl.append(p_pr)
    if bullet:
        r_pr = OxmlElement("w:rPr")
        fonts = OxmlElement("w:rFonts")
        fonts.set(qn("w:ascii"), "Symbol")
        fonts.set(qn("w:hAnsi"), "Symbol")
        r_pr.append(fonts)
        lvl.append(r_pr)
    abstract.append(lvl)
    numbering.append(abstract)
    num_ids = [int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num"))]
    num_id = max(num_ids, default=0) + 1
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abs_ref = OxmlElement("w:abstractNumId")
    abs_ref.set(qn("w:val"), str(abs_id))
    num.append(abs_ref)
    numbering.append(num)
    return num_id


def apply_num(paragraph, num_id):
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is None:
        num_pr = OxmlElement("w:numPr")
        p_pr.append(num_pr)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num = OxmlElement("w:numId")
    num.set(qn("w:val"), str(num_id))
    num_pr.append(ilvl)
    num_pr.append(num)


def add_field(paragraph, instr):
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), instr)
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "1"
    run.append(text)
    fld.append(run)
    paragraph._p.append(fld)


def set_header_footer(section, first=False):
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run("SYSTEMATIC SCOPING REVIEW  |  ACL ARR 2026")
    set_run_font(r, size=8.5, color=MUTED, bold=True)
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    fp.paragraph_format.space_before = Pt(0)
    rr = fp.add_run("Page ")
    set_run_font(rr, size=8.5, color=MUTED)
    add_field(fp, "PAGE")


def setup_page(section):
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    set_header_footer(section)


def add_cover(doc):
    for _ in range(5):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(14)
    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker.paragraph_format.space_after = Pt(18)
    r = kicker.add_run("SYSTEMATIC SCOPING REVIEW")
    set_run_font(r, size=10.5, color=GOLD, bold=True)
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(10)
    r = title.add_run("Computational Qualitative Analysis with Large Language Models")
    set_run_font(r, size=29, color=INK, bold=True)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(8)
    r = sub.add_run("Methods, human roles, evaluation validity, provenance, confounds, and a defensible ACL ARR research agenda")
    set_run_font(r, size=14, color=DARK_BLUE)
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_before = Pt(34)
    meta.paragraph_format.space_after = Pt(8)
    r = meta.add_run("Search cutoff: 24 August 2026  •  Target cycle: 12 October 2026 ACL Rolling Review")
    set_run_font(r, size=10.5, color=MUTED, bold=True)
    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_after = Pt(0)
    r = note.add_run("Single-reviewer, computationally assisted scoping review; companion evidence workbook supplied")
    set_run_font(r, size=9.5, color=MUTED, italic=True)
    doc.add_page_break()


def widths_for(n):
    patterns = {
        2: [2700, 6660],
        3: [2160, 3600, 3600],
        4: [1500, 2760, 2580, 2520],
        5: [1200, 2040, 2040, 2040, 2040],
    }
    if n in patterns:
        return patterns[n]
    each = 9360 // n
    widths = [each] * n
    widths[-1] += 9360 - sum(widths)
    return widths


def add_md_table(doc, rows):
    ncols = max(len(row) for row in rows)
    rows = [row + [""] * (ncols - len(row)) for row in rows]
    table = doc.add_table(rows=len(rows), cols=ncols)
    set_table_geometry(table, widths_for(ncols))
    apply_table_borders(table)
    set_repeat_table_header(table.rows[0])
    for ri, row in enumerate(rows):
        for ci, value in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_inline(p, value, default_size=8.5, default_color="000000")
            if ri == 0:
                shade_cell(cell, LIGHT)
                for run in p.runs:
                    run.bold = True
                    run.font.color.rgb = RGBColor.from_string(INK)
            elif ri % 2 == 0:
                shade_cell(cell, "FAFBFC")
    cap = doc.add_paragraph(style="Table Citation")
    cap.add_run("Source: reviewer synthesis from the cited primary studies; full row-level extraction is in the companion workbook.")


def parse_table(lines, start):
    block, i = [], start
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        block.append(lines[i].strip())
        i += 1
    rows = []
    for idx, line in enumerate(block):
        vals = [x.strip() for x in line.strip("|").split("|")]
        if idx == 1 and all(re.fullmatch(r":?-{3,}:?", x or "") for x in vals):
            continue
        rows.append(vals)
    return rows, i


def add_callout(doc, text):
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [9360])
    apply_table_borders(table)
    shade_cell(table.cell(0, 0), LIGHT)
    p = table.cell(0, 0).paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    add_inline(p, text, default_size=10.5, default_color=INK)


def parse_markdown(doc, text):
    lines = text.splitlines()
    bullet_num = add_custom_numbering(doc, True)
    decimal_num = add_custom_numbering(doc, False)
    i = 0
    first_h1 = True
    while i < len(lines):
        raw = lines[i].rstrip()
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("|"):
            rows, i = parse_table(lines, i)
            if rows:
                add_md_table(doc, rows)
            continue
        hm = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if hm:
            level = len(hm.group(1))
            title = hm.group(2)
            if level == 1:
                if first_h1:
                    first_h1 = False
                else:
                    doc.add_page_break()
            p = doc.add_paragraph(style=f"Heading {level}")
            add_inline(p, title, default_size={1:16, 2:13, 3:12}[level], default_color={1:BLUE, 2:BLUE, 3:DARK_BLUE}[level])
            i += 1
            continue
        if stripped.startswith("> "):
            add_callout(doc, stripped[2:])
            i += 1
            continue
        bm = re.match(r"^[-*]\s+(.+)$", stripped)
        nm = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if bm or nm:
            p = doc.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            apply_num(p, bullet_num if bm else decimal_num)
            add_inline(p, (bm or nm).group(1))
            i += 1
            continue
        para = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or re.match(r"^(#{1,3})\s+", nxt) or nxt.startswith("|") or nxt.startswith("> ") or re.match(r"^[-*]\s+", nxt) or re.match(r"^\d+[.)]\s+", nxt):
                break
            para.append(nxt)
            i += 1
        paragraph_text = " ".join(para)
        p = doc.add_paragraph()
        # Long file paths, schema field names, and SHA-256 fingerprints create
        # distracting rivers of whitespace when a justified line has only a
        # few unbreakable tokens.  Keep those audit paragraphs left-aligned.
        if "`" in paragraph_text or re.search(r"\b[0-9a-f]{32,}\b", paragraph_text, re.IGNORECASE):
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        add_inline(p, paragraph_text)


def structural_audit(path):
    with zipfile.ZipFile(path) as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8")
        styles_xml = zf.read("word/styles.xml").decode("utf-8")
        numbering_xml = zf.read("word/numbering.xml").decode("utf-8")
    checks = {
        "letter_page_size": 'w:w="12240"' in document_xml and 'w:h="15840"' in document_xml,
        "one_inch_margins": all(token in document_xml for token in ['w:top="1440"', 'w:right="1440"', 'w:bottom="1440"', 'w:left="1440"']),
        "header_footer_distance": 'w:header="708"' in document_xml and 'w:footer="708"' in document_xml,
        "fixed_table_layout": 'w:tblLayout w:type="fixed"' in document_xml,
        "full_width_tables": bool(re.search(r'w:tblW\s+(?:w:type="dxa"\s+w:w="9360"|w:w="9360"\s+w:type="dxa")', document_xml)),
        "table_indent_120": 'w:tblInd w:w="120" w:type="dxa"' in document_xml,
        "custom_list_indent": 'w:left="540" w:hanging="280"' in numbering_xml,
        "normal_spacing": 'w:line="320"' in styles_xml and 'w:after="160"' in styles_xml,
        "heading_colors": BLUE in styles_xml and DARK_BLUE in styles_xml,
        "no_placeholder_tokens": not any(token in document_xml for token in ("TODO", "TBD", "PLACEHOLDER", "{{")),
    }
    return {"preset": "narrative_proposal", "header_pattern": "editorial_cover", "named_overrides": ["cover_title_29pt", "table_body_8.5pt", "table_line_spacing_1.15", "H1_page_breaks"], "checks": checks, "all_passed": all(checks.values())}


def main():
    if not SOURCE.exists():
        raise SystemExit(f"Missing {SOURCE}")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    setup_page(doc.sections[0])
    setup_styles(doc)
    core = doc.core_properties
    core.title = "Computational Qualitative Analysis with Large Language Models: Systematic Scoping Review"
    core.subject = "Thematic analysis, qualitative coding, evaluation validity, provenance, and ACL ARR research directions"
    core.author = "Systematic review team"
    core.keywords = "LLM, qualitative analysis, thematic analysis, coding, provenance, evaluation, ACL ARR"
    add_cover(doc)
    parse_markdown(doc, SOURCE.read_text(encoding="utf-8"))
    doc.save(OUT)
    audit = structural_audit(OUT)
    AUDIT.write_text(json.dumps(audit, indent=2))
    if not audit["all_passed"]:
        raise SystemExit(f"Design audit failed: {json.dumps(audit, indent=2)}")
    print(OUT)
    print(AUDIT)


if __name__ == "__main__":
    main()
