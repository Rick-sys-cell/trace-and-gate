"""Edit a python-pptx deck built only from text boxes, shapes, tables and pictures (the interim deck).

Text is replaced run by run, so each paragraph keeps its template formatting: run i of a new
paragraph copies run i of the template paragraph (or its last run). Slides are duplicated by
deep-copying the shape tree and re-pointing image relationships.
"""
from __future__ import annotations

from copy import deepcopy

from PIL import Image
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches

EMU_PER_IN = 914400


def _runs_of(item):
    return [item] if isinstance(item, str) else list(item)


def _fill_paragraph(p, runs):
    old = p.findall(qn("a:r"))
    templates = [deepcopy(r) for r in old]
    for el in old + p.findall(qn("a:br")) + p.findall(qn("a:fld")):
        p.remove(el)
    if not templates:
        r = p.makeelement(qn("a:r"), {})
        r.append(r.makeelement(qn("a:t"), {}))
        templates = [r]
    end = p.find(qn("a:endParaRPr"))
    for i, text in enumerate(runs):
        r = deepcopy(templates[min(i, len(templates) - 1)])
        r.find(qn("a:t")).text = text
        if end is not None:
            end.addprevious(r)
        else:
            p.append(r)


def fill_body(tx_body, items):
    """Set a txBody's paragraphs: items is a string or a list of paragraphs, each a string or a list of runs."""
    items = [items] if isinstance(items, str) else list(items)
    paras = tx_body.findall(qn("a:p"))
    for i, item in enumerate(items):
        if i < len(paras):
            p = paras[i]
        else:
            p = deepcopy(paras[-1])
            paras[-1].addnext(p)
            paras.append(p)
        _fill_paragraph(p, _runs_of(item))
    for p in paras[len(items):]:
        tx_body.remove(p)


def set_text(shape, items):
    fill_body(shape.text_frame._txBody, items)


def recolor(cell, hex_rgb):
    """Set the text colour of every run in a table cell."""
    for clr in cell._tc.iter(qn("a:rPr")):
        for fill in clr.findall(qn("a:solidFill")):
            clr.remove(fill)
        fill = clr.makeelement(qn("a:solidFill"), {})
        fill.append(fill.makeelement(qn("a:srgbClr"), {"val": hex_rgb}))
        clr.insert(0, fill)


def set_line(shape, i, item):
    """Replace paragraph i of a shape's text only (a string or a list of runs)."""
    _fill_paragraph(shape.text_frame._txBody.findall(qn("a:p"))[i], _runs_of(item))


def all_shapes(shapes):
    """Every shape, including those inside groups."""
    for sh in shapes:
        yield sh
        if sh.shape_type == 6:
            yield from all_shapes(sh.shapes)


def by_text(slide, start):
    """The shape whose text starts with `start` (exactly one; groups included)."""
    hits = [s for s in all_shapes(slide.shapes) if s.has_text_frame and s.text_frame.text.startswith(start)]
    if len(hits) != 1:
        raise KeyError(f"{len(hits)} shapes start with {start!r}")
    return hits[0]


def by_name(slide, name):
    hits = [s for s in slide.shapes if s.name == name]
    if len(hits) != 1:
        raise KeyError(f"{len(hits)} shapes named {name!r}")
    return hits[0]


def tables(slide):
    return [s for s in slide.shapes if s.has_table]


def pictures(slide):
    return [s for s in slide.shapes if s.shape_type == 13]


def remove(shape):
    shape._element.getparent().remove(shape._element)


def move(shape, left=None, top=None, width=None, height=None):
    for attr, v in (("left", left), ("top", top), ("width", width), ("height", height)):
        if v is not None:
            setattr(shape, attr, Inches(v))


def fill_table(shape, rows, widths=None, row_height=None):
    """Replace a table's cells. rows[0] is the header. Rows and columns are added by copying the
    last ones of the template (data rows alternate between the template's first two data rows, to
    keep its banding) and removed from the end. widths (inches) must sum to the frame width."""
    tbl = shape.table._tbl
    ncols = max(len(r) for r in rows)
    grid = tbl.tblGrid
    cols = grid.findall(qn("a:gridCol"))
    while len(cols) < ncols:
        cols[-1].addnext(deepcopy(cols[-1]))
        for tr in tbl.findall(qn("a:tr")):
            tcs = tr.findall(qn("a:tc"))
            tcs[-1].addnext(deepcopy(tcs[-1]))
        cols = grid.findall(qn("a:gridCol"))
    while len(cols) > ncols:
        grid.remove(cols[-1])
        for tr in tbl.findall(qn("a:tr")):
            tr.remove(tr.findall(qn("a:tc"))[-1])
        cols = grid.findall(qn("a:gridCol"))
    trs = tbl.findall(qn("a:tr"))
    data_protos = [deepcopy(tr) for tr in trs[1:3]] or [deepcopy(trs[0])]
    while len(trs) < len(rows):
        new = deepcopy(data_protos[(len(trs) - 1) % len(data_protos)])
        trs[-1].addnext(new)
        trs = tbl.findall(qn("a:tr"))
    for tr in trs[len(rows):]:
        tbl.remove(tr)
    trs = tbl.findall(qn("a:tr"))
    for tr, row in zip(trs, rows):
        for tc, cell in zip(tr.findall(qn("a:tc")), list(row) + [""] * (ncols - len(row))):
            fill_body(tc.find(qn("a:txBody")), cell)
        if row_height is not None:
            tr.set("h", str(int(row_height * EMU_PER_IN)))
    if widths:
        total = sum(widths)
        for col, w in zip(grid.findall(qn("a:gridCol")), widths):
            col.set("w", str(int(w * shape.width / total)))
    shape.height = sum(int(tr.get("h")) for tr in trs)


def replace_picture(slide, pic, path, fit=True):
    """Point a picture at a new image file; with fit, scale it into the old box keeping its aspect."""
    _, rid = slide.part.get_or_add_image_part(str(path))
    fill = pic._element.blipFill
    fill.find(qn("a:blip")).set(qn("r:embed"), rid)
    crop = fill.find(qn("a:srcRect"))
    if crop is not None:
        fill.remove(crop)
    if fit:
        w, h = Image.open(path).size
        box_w, box_h = pic.width, pic.height
        scale = min(box_w / w, box_h / h)
        pic.width, pic.height = int(w * scale), int(h * scale)


def duplicate(prs, src):
    """Append a copy of slide `src` (shapes, background, images, notes) and return it."""
    new = prs.slides.add_slide(src.slide_layout)
    for sh in list(new.shapes):
        remove(sh)
    tree = new.shapes._spTree
    for el in src.shapes._spTree:
        if el.tag in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
            continue
        tree.append(deepcopy(el))
    bg = src._element.cSld.bg
    if bg is not None:
        new._element.cSld.insert(0, deepcopy(bg))
    for el in tree.iter():
        for attr in (qn("r:embed"), qn("r:link"), qn("r:id")):
            rid = el.get(attr)
            if rid and rid in src.part.rels:
                rel = src.part.rels[rid]
                new_rid = (new.part.relate_to(rel.target_ref, rel.reltype, is_external=True) if rel.is_external
                           else new.part.relate_to(rel.target_part, rel.reltype))
                el.set(attr, new_rid)
    if src.has_notes_slide:
        new.notes_slide.notes_text_frame.text = src.notes_slide.notes_text_frame.text
    return new


def reorder(prs, slides):
    """Keep exactly `slides`, in this order; every other slide is dropped from the deck."""
    sld_ids = prs.slides._sldIdLst
    by_part = {prs.part.related_part(s.get(qn("r:id"))): s for s in list(sld_ids)}
    keep = [by_part[s.part] for s in slides]
    for el in list(sld_ids):
        sld_ids.remove(el)
        if el not in keep:
            prs.part.drop_rel(el.get(qn("r:id")))
    for el in keep:
        sld_ids.append(el)


def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def inches(v):
    return Emu(v).inches
