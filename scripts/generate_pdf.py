#!/usr/bin/env python3
"""Build a single navigable PDF from the TPL .dat template library.

Structure:
  * Master Table of Contents  -> folder full names (links to each folder TOC)
  * One Folder TOC per folder -> case ids + descriptions (links to each .dat)
  * Each .dat file            -> starts on its own page, with line numbers

Internal hyperlinks (clickable) + a PDF outline (bookmark sidebar) are added.
"""
import os
import sys

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_tpl import build_model  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "TPL_Template_Library.pdf"

# ---- geometry ---------------------------------------------------------------
PAGE_W, PAGE_H = letter          # 612 x 792
L_MARGIN = 50
R_MARGIN = 40
T_MARGIN = 46
B_MARGIN = 44
CONTENT_TOP = PAGE_H - T_MARGIN
CONTENT_BOT = B_MARGIN

# ---- colours ----------------------------------------------------------------
INK = HexColor("#1a1a1a")
LINK = HexColor("#1551b5")
MUTED = HexColor("#6b7280")
RULE = HexColor("#c9ced6")
NUMCOL = HexColor("#9aa1ab")
BAND = HexColor("#eef2f8")
ACCENT = HexColor("#0b3d91")

# ---- monospace content layout ----------------------------------------------
MONO = "Courier"
MONO_SIZE = 7.5
MONO_LEAD = 9.3
CHAR_W = stringWidth("0", MONO, MONO_SIZE)   # fixed width for Courier
TABSTOP = 8


def expand_tabs(s, tabsize=TABSTOP):
    return s.expandtabs(tabsize)


def sanitize(s):
    """Keep it printable for the WinAnsi Courier font."""
    out = []
    for ch in s:
        o = ord(ch)
        if ch in ("\t",):
            out.append(ch)
        elif o == 9:
            out.append(" ")
        elif o < 32 or o == 127:
            out.append(".")      # control chars -> dot
        elif o > 0x255 and o not in (0x2013, 0x2014, 0x2018, 0x2019, 0x201c, 0x201d):
            out.append("?")
        else:
            out.append(ch)
    return "".join(out)


class Doc:
    def __init__(self, path):
        self.c = canvas.Canvas(path, pagesize=letter, pageCompression=1)
        self.c.setTitle("GEM Template Library")
        self.c.setAuthor("TPL -> PDF organizer")
        self.y = CONTENT_TOP
        self.page_started = False

    # -- link helper: draw text and overlay a clickable rectangle -------------
    def link_text(self, x, y, text, dest, font, size, color=LINK,
                  underline=True, maxx=None):
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        self.c.drawString(x, y, text)
        w = stringWidth(text, font, size)
        if maxx is not None:
            w = min(w, maxx - x)
        if underline:
            self.c.setStrokeColor(color)
            self.c.setLineWidth(0.4)
            self.c.line(x, y - 1.6, x + w, y - 1.6)
        self.c.linkRect("", dest, (x, y - 2.5, x + w, y + size),
                        relative=1, thickness=0)
        self.c.setFillColor(INK)
        return w

    def rule(self, y, x0=L_MARGIN, x1=PAGE_W - R_MARGIN, color=RULE, w=0.6):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(w)
        self.c.line(x0, y, x1, y)

    def new_page(self):
        if self.page_started:
            self.c.showPage()
        self.page_started = True
        self.y = CONTENT_TOP

    def footer(self, label):
        self.c.setFont("Helvetica", 7)
        self.c.setFillColor(MUTED)
        self.c.drawRightString(PAGE_W - R_MARGIN, 26, label)
        self.c.drawString(L_MARGIN, 26, "GEM Template Library")
        self.c.setFillColor(INK)

    def save(self):
        if self.page_started:
            self.c.showPage()
        self.c.save()


def wrap_mono(text, width_chars):
    if width_chars < 8:
        width_chars = 8
    if len(text) <= width_chars:
        return [text] if text else [""]
    rows = []
    i = 0
    n = len(text)
    while i < n:
        rows.append(text[i:i + width_chars])
        i += width_chars
    return rows or [""]


def build(folders, out_path):
    doc = Doc(out_path)
    c = doc.c
    total_cases = sum(len(f["cases"]) for f in folders)

    # ====================== MASTER TOC ======================
    doc.new_page()
    c.bookmarkPage("master_toc")
    c.addOutlineEntry("Master Table of Contents", "master_toc", level=0, closed=False)

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(L_MARGIN, doc.y - 6, "GEM Template Library")
    doc.y -= 30
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(L_MARGIN, doc.y, "Master Table of Contents")
    doc.y -= 16
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(L_MARGIN, doc.y,
                 f"{len(folders)} categories  ·  {total_cases} data (.dat) templates. "
                 "Click a category to open its table of contents.")
    doc.y -= 12
    doc.rule(doc.y)
    doc.y -= 20
    c.setFillColor(INK)

    for f in folders:
        if doc.y < CONTENT_BOT + 24:
            doc.footer("Master Table of Contents")
            doc.new_page()
            c.setFont("Helvetica-Bold", 13)
            c.drawString(L_MARGIN, doc.y, "Master Table of Contents (continued)")
            doc.y -= 20
        n = len(f["cases"])
        # category code chip
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(MUTED)
        c.drawString(L_MARGIN, doc.y, f["code"].upper())
        # full name as link
        doc.link_text(L_MARGIN + 46, doc.y, f["title"], f"toc_{f['code']}",
                      "Helvetica-Bold", 11.5)
        # count at right
        c.setFont("Helvetica", 9)
        c.setFillColor(MUTED)
        lab = f"{n} template" + ("s" if n != 1 else "")
        c.drawRightString(PAGE_W - R_MARGIN, doc.y, lab)
        c.setFillColor(INK)
        doc.y -= 10
        doc.rule(doc.y + 3, color=HexColor("#eceff3"), w=0.4)
        doc.y -= 11
    doc.footer("Master Table of Contents")

    # ====================== PER-FOLDER SECTIONS ======================
    for f in folders:
        render_folder_toc(doc, f)
        for case in f["cases"]:
            render_dat(doc, f, case)

    doc.save()


def render_folder_toc(doc, f):
    c = doc.c
    doc.new_page()
    c.bookmarkPage(f"toc_{f['code']}")
    c.addOutlineEntry(f["title"], f"toc_{f['code']}", level=0, closed=True)

    # header band
    c.setFillColor(BAND)
    c.rect(0, doc.y - 30, PAGE_W, 44, stroke=0, fill=1)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(L_MARGIN, doc.y - 4, f["title"])
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawString(L_MARGIN, doc.y - 18,
                 f"Category {f['code'].upper()}  ·  {len(f['cases'])} templates")
    doc.link_text(PAGE_W - R_MARGIN - 118, doc.y - 18, "↑ Master Table of Contents",
                  "master_toc", "Helvetica", 8.5)
    doc.y -= 44
    c.setFillColor(INK)

    def toc_header_cont():
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(ACCENT)
        c.drawString(L_MARGIN, doc.y, f"{f['title']} (continued)")
        c.setFillColor(INK)
        doc.y -= 16

    for case in f["cases"]:
        code = os.path.splitext(case["name"])[0]
        desc = case["desc"] or "—"
        # measure wrapped description
        code_w = 74
        desc_x = L_MARGIN + code_w
        avail = (PAGE_W - R_MARGIN) - desc_x
        lines = simple_wrap(desc, "Helvetica", 9.5, avail)
        need = max(12, len(lines) * 11 + 4)
        if doc.y < CONTENT_BOT + need:
            doc.footer(f["title"])
            doc.new_page()
            toc_header_cont()
        # code as link (also covers whole first row)
        doc.link_text(L_MARGIN, doc.y, code, f"dat_{case['key']}",
                      "Helvetica-Bold", 9.5, underline=True)
        c.setFillColor(INK)
        c.setFont("Helvetica", 9.5)
        first = True
        for ln in lines:
            if not first:
                doc.y -= 11
            c.setFillColor(INK)
            c.drawString(desc_x, doc.y, ln)
            first = False
        doc.y -= 13
        doc.rule(doc.y + 4, color=HexColor("#eceff3"), w=0.4)
        doc.y -= 2
    doc.footer(f["title"])


def simple_wrap(text, font, size, avail):
    words = text.split()
    if not words:
        return [""]
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if stringWidth(trial, font, size) <= avail:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            # hard-split very long words
            while stringWidth(w, font, size) > avail and len(w) > 1:
                lo, hi = 1, len(w)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if stringWidth(w[:mid], font, size) <= avail:
                        lo = mid
                    else:
                        hi = mid - 1
                lines.append(w[:lo])
                w = w[lo:]
            cur = w
    if cur:
        lines.append(cur)
    return lines


def read_dat(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        txt = raw.decode("cp1252", errors="replace")
    return txt.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def render_dat(doc, f, case):
    c = doc.c
    code = os.path.splitext(case["name"])[0]
    doc.new_page()
    c.bookmarkPage(f"dat_{case['key']}")
    c.addOutlineEntry(f"{code} — {case['desc'][:60]}" if case["desc"] else code,
                      f"dat_{case['key']}", level=1, closed=True)

    src = read_dat(case["path"])
    # drop a single trailing empty line produced by terminal newline
    if src and src[-1] == "":
        src.pop()

    # ---- header band ----
    def draw_header(cont=False):
        c.setFillColor(BAND)
        c.rect(0, doc.y - 26, PAGE_W, 40, stroke=0, fill=1)
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 12)
        title = case["name"] + ("  (continued)" if cont else "")
        c.drawString(L_MARGIN, doc.y - 2, title)
        # back links top-right
        bx = PAGE_W - R_MARGIN
        w1 = stringWidth("Master TOC", "Helvetica", 8.5)
        doc.link_text(bx - w1, doc.y - 2, "Master TOC", "master_toc",
                      "Helvetica", 8.5)
        lbl2 = f"{f['code'].upper()} TOC"
        w2 = stringWidth(lbl2, "Helvetica", 8.5)
        doc.link_text(bx - w1 - 14 - w2, doc.y - 2, lbl2, f"toc_{f['code']}",
                      "Helvetica", 8.5)
        if not cont and case["desc"]:
            c.setFont("Helvetica-Oblique", 8)
            c.setFillColor(MUTED)
            dl = simple_wrap(case["desc"], "Helvetica-Oblique", 8,
                             (PAGE_W - R_MARGIN) - L_MARGIN)
            c.drawString(L_MARGIN, doc.y - 15, dl[0][:200])
        c.setFillColor(INK)

    draw_header(cont=False)
    doc.y -= 40

    # ---- content layout ----
    ndigits = max(4, len(str(len(src))))
    gutter_w = ndigits * CHAR_W + 10          # number column width
    num_right = L_MARGIN + ndigits * CHAR_W    # right edge for right-aligned num
    text_x = L_MARGIN + gutter_w
    avail_w = (PAGE_W - R_MARGIN) - text_x
    width_chars = max(8, int(avail_w / CHAR_W))

    # Render each page's line numbers and content as single text objects
    # (one BT/ET each) instead of per-line draw calls -- this keeps the
    # content streams compact for very large files.
    def start_content_to():
        t = c.beginText(text_x, doc.y)
        t.setFont(MONO, MONO_SIZE)
        t.setLeading(MONO_LEAD)
        t.setFillColor(INK)
        return t

    content_to = start_content_to()
    num_cmds = []   # (x, y, number_string) for the current page

    def flush_page():
        c.drawText(content_to)
        if num_cmds:
            nt = c.beginText()
            nt.setFont(MONO, MONO_SIZE)
            nt.setLeading(MONO_LEAD)
            nt.setFillColor(NUMCOL)
            for x, y, s in num_cmds:
                nt.setTextOrigin(x, y)
                nt.textLine(s)
            c.drawText(nt)

    for i, raw_line in enumerate(src, start=1):
        line = sanitize(expand_tabs(raw_line))
        vis = wrap_mono(line, width_chars)
        for j, seg in enumerate(vis):
            if doc.y < CONTENT_BOT + MONO_LEAD:
                flush_page()
                doc.footer(case["name"])
                doc.new_page()
                draw_header(cont=True)
                doc.y -= 40
                content_to = start_content_to()
                num_cmds = []
            if j == 0:
                nx = num_right - len(str(i)) * CHAR_W
                num_cmds.append((nx, doc.y, str(i)))
            content_to.textLine(seg)
            doc.y -= MONO_LEAD
    flush_page()
    doc.footer(case["name"])


def compress_pdf(path):
    """Shrink the file by de-duplicating identical objects and recompressing
    page content streams. Keeps the outline and all internal links intact.
    No-op if pypdf is not installed."""
    try:
        from pypdf import PdfWriter
    except Exception:
        print("pypdf not available; skipping compression step")
        return
    w = PdfWriter(clone_from=path)
    try:
        w.compress_identical_objects(remove_duplicates=True,
                                     remove_unreferenced=True)
    except TypeError:  # older pypdf keyword names
        w.compress_identical_objects(remove_identicals=True,
                                     remove_orphans=True)
    for p in w.pages:
        try:
            p.compress_content_streams()
        except Exception:
            pass
    w.write(path)


if __name__ == "__main__":
    folders = build_model()
    build(folders, OUT)
    compress_pdf(OUT)
    print("wrote", OUT)
