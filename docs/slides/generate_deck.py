"""
docs/slides/generate_deck.py
------------------------------
Builds the mid-term progress update slide deck as an actual .pptx file
(not a screenshot or export) using python-pptx. All diagrams are drawn
with native PowerPoint shapes and connectors, so they stay fully editable
in PowerPoint afterward.

Run:
    pip install python-pptx     (already added to requirements.txt)
    python docs/slides/generate_deck.py

Output:
    docs/slides/Midterm_Progress_Update.pptx

To update the deck later: edit the CONTENT section near the bottom of this
file (plain Python lists/strings) and re-run the script. Re-running always
overwrites the .pptx from scratch, so any manual edits made directly inside
PowerPoint will be lost on the next run.
"""

from __future__ import annotations
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

# ── Theme ──────────────────────────────────────────────────────────────────
NAVY = RGBColor(0x14, 0x2A, 0x4A)       # header bars, primary boxes
BLUE = RGBColor(0x1F, 0x6F, 0xEB)       # accent rule, secondary boxes
GREEN = RGBColor(0x1E, 0x8C, 0x5A)      # highlight = the proposed hybrid system
AMBER = RGBColor(0xC9, 0x8A, 0x11)      # "in progress" status
GRAY = RGBColor(0x8A, 0x8F, 0x98)       # "upcoming / not started" status
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_DARK = RGBColor(0x2B, 0x2E, 0x33)
LIGHT_BG = RGBColor(0xF5, 0xF7, 0xFA)

FONT = "Calibri"
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
FOOTER_TEXT = "Fine-Tuning vs RAG vs Hybrid Code Completion"


def new_presentation() -> Presentation:
    """Creates a blank 16:9 presentation sized to standard widescreen."""
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs):
    """Adds a completely blank slide so every element on it is placed by us,
    which is what keeps every slide visually consistent."""
    layout = prs.slide_layouts[6]  # 6 = blank layout in the default template
    return prs.slides.add_slide(layout)


# ── Shared chrome (header bar, accent rule, footer) applied to every slide ──

def add_header(slide, title_text: str, kicker: str = ""):
    """Draws the navy header bar + accent rule + title text used on every
    content slide, so the deck reads as one consistent template."""
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(1.15))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    bar.shadow.inherit = False

    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(1.15), SLIDE_W, Pt(4))
    rule.fill.solid()
    rule.fill.fore_color.rgb = BLUE
    rule.line.fill.background()
    rule.shadow.inherit = False

    if kicker:
        kb = slide.shapes.add_textbox(Inches(0.5), Inches(0.12), Inches(10), Inches(0.3))
        kp = kb.text_frame.paragraphs[0]
        kp.text = kicker.upper()
        kp.font.size = Pt(11)
        kp.font.color.rgb = BLUE
        kp.font.name = FONT
        kp.font.bold = True

    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.38), Inches(12.3), Inches(0.7))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT


def add_footer(slide, slide_num: int):
    """Small consistent footer: project tag on the left, slide number on the right."""
    fb = slide.shapes.add_textbox(Inches(0.5), Inches(7.15), Inches(9), Inches(0.3))
    fp = fb.text_frame.paragraphs[0]
    fp.text = FOOTER_TEXT
    fp.font.size = Pt(9)
    fp.font.color.rgb = GRAY
    fp.font.name = FONT

    nb = slide.shapes.add_textbox(Inches(12.4), Inches(7.15), Inches(0.6), Inches(0.3))
    npara = nb.text_frame.paragraphs[0]
    npara.text = str(slide_num)
    npara.font.size = Pt(9)
    npara.font.color.rgb = GRAY
    npara.font.name = FONT
    npara.alignment = PP_ALIGN.RIGHT


# ── Slide builders ────────────────────────────────────────────────────────

def add_title_slide(prs, title, subtitle, meta_lines):
    """The cover slide: full navy background, big centered title, meta info at the bottom."""
    slide = blank_slide(prs)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    bg.shadow.inherit = False

    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(3.55), Inches(2.2), Pt(6))
    accent.fill.solid()
    accent.fill.fore_color.rgb = GREEN
    accent.line.fill.background()
    accent.shadow.inherit = False
    accent.left = Inches(0.9)

    tb = slide.shapes.add_textbox(Inches(0.9), Inches(2.3), Inches(11.5), Inches(1.2))
    p = tb.text_frame.paragraphs[0]
    tb.text_frame.word_wrap = True
    p.text = title
    p.font.size = Pt(34)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT

    sb = slide.shapes.add_textbox(Inches(0.9), Inches(3.7), Inches(11.5), Inches(0.6))
    sp = sb.text_frame.paragraphs[0]
    sp.text = subtitle
    sp.font.size = Pt(20)
    sp.font.color.rgb = BLUE
    sp.font.name = FONT
    sp.font.bold = True

    mb = slide.shapes.add_textbox(Inches(0.9), Inches(6.3), Inches(11.5), Inches(1.0))
    tf = mb.text_frame
    for i, line in enumerate(meta_lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(13)
        p.font.color.rgb = RGBColor(0xC9, 0xD6, 0xE8)
        p.font.name = FONT
    return slide


def _bullet_paragraph(tf, text, level, first):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    prefix = "-  " if level == 0 else "     - "
    p.text = f"{prefix}{text}"
    p.font.size = Pt(18) if level == 0 else Pt(15)
    p.font.color.rgb = TEXT_DARK
    p.font.name = FONT
    p.space_after = Pt(10) if level == 0 else Pt(6)
    return p


def add_bullet_slide(prs, slide_num, title, bullets, kicker=""):
    """Standard content slide: header + a left-aligned bullet list.
    `bullets` is a list of (text, level) tuples, level 0 = top-level, 1 = sub-bullet.
    """
    slide = blank_slide(prs)
    add_header(slide, title, kicker)
    box = slide.shapes.add_textbox(Inches(0.7), Inches(1.55), Inches(11.9), Inches(5.4))
    tf = box.text_frame
    tf.word_wrap = True
    for i, (text, level) in enumerate(bullets):
        _bullet_paragraph(tf, text, level, first=(i == 0))
    add_footer(slide, slide_num)
    return slide


def add_flow_diagram(slide, labels, y_in, box_w_in=2.1, box_h_in=0.9, gap_in=0.55, highlight_idx=None):
    """
    Draws a left-to-right box-and-arrow pipeline diagram, centered horizontally.
    `labels` is a list of strings, one per box. `highlight_idx` optionally
    marks one box (e.g. the proposed system) in green instead of navy/blue.
    """
    n = len(labels)
    total_w = n * box_w_in + (n - 1) * gap_in
    start_x = (13.333 - total_w) / 2
    y = Inches(y_in)

    centers = []
    for i, label in enumerate(labels):
        x = Inches(start_x + i * (box_w_in + gap_in))
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, Inches(box_w_in), Inches(box_h_in))
        shape.fill.solid()
        shape.fill.fore_color.rgb = GREEN if i == highlight_idx else (BLUE if i % 2 else NAVY)
        shape.line.color.rgb = WHITE
        shape.line.width = Pt(1)
        shape.shadow.inherit = False
        tf = shape.text_frame
        tf.word_wrap = True
        tf.margin_left = Emu(45720)
        tf.margin_right = Emu(45720)
        p = tf.paragraphs[0]
        p.text = label
        p.font.size = Pt(12.5)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.font.name = FONT
        p.alignment = PP_ALIGN.CENTER
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        centers.append((x, y, Inches(box_w_in), Inches(box_h_in)))

    for i in range(n - 1):
        x1, y1, w1, h1 = centers[i]
        x2, y2, w2, h2 = centers[i + 1]
        conn = slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT,
            int(x1) + int(w1), int(y1) + int(h1) / 2,
            int(x2), int(y2) + int(h2) / 2,
        )
        conn.line.color.rgb = GRAY
        conn.line.width = Pt(2.25)
        _set_arrowhead(conn)


def _set_arrowhead(connector):
    """python-pptx has no high-level arrowhead API, so this pokes the
    underlying XML directly to add a triangular arrow tip at the line end."""
    ln = connector.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)


def add_diagram_slide(prs, slide_num, title, labels, highlight_idx, caption_bullets, kicker=""):
    """A slide with a flow diagram at the top and a few explanatory bullets below it."""
    slide = blank_slide(prs)
    add_header(slide, title, kicker)
    add_flow_diagram(slide, labels, y_in=1.9, highlight_idx=highlight_idx)

    box = slide.shapes.add_textbox(Inches(0.9), Inches(3.3), Inches(11.5), Inches(3.4))
    tf = box.text_frame
    tf.word_wrap = True
    for i, text in enumerate(caption_bullets):
        _bullet_paragraph(tf, text, 0, first=(i == 0))
    add_footer(slide, slide_num)
    return slide


def add_three_box_slide(prs, slide_num, title, systems, kicker=""):
    """
    Three side-by-side cards summarizing the systems under comparison.
    `systems` is a list of (name, description, is_proposed) tuples.
    """
    slide = blank_slide(prs)
    add_header(slide, title, kicker)

    n = len(systems)
    card_w, gap, y = 3.9, 0.35, 1.9
    total_w = n * card_w + (n - 1) * gap
    start_x = (13.333 - total_w) / 2

    for i, (name, desc, proposed) in enumerate(systems):
        x = Inches(start_x + i * (card_w + gap))
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(y), Inches(card_w), Inches(4.3))
        card.fill.solid()
        card.fill.fore_color.rgb = GREEN if proposed else LIGHT_BG
        card.line.color.rgb = GREEN if proposed else GRAY
        card.line.width = Pt(1.5)
        card.shadow.inherit = False

        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.25)
        tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.25)

        p = tf.paragraphs[0]
        p.text = ("PROPOSED  " if proposed else "") + name
        p.font.bold = True
        p.font.size = Pt(16)
        p.font.color.rgb = WHITE if proposed else NAVY
        p.font.name = FONT
        p.space_after = Pt(10)

        for line in desc:
            dp = tf.add_paragraph()
            dp.text = f"-  {line}"
            dp.font.size = Pt(13)
            dp.font.color.rgb = WHITE if proposed else TEXT_DARK
            dp.font.name = FONT
            dp.space_after = Pt(8)

    add_footer(slide, slide_num)
    return slide


def add_table_slide(prs, slide_num, title, headers, rows, col_widths_in=None, kicker=""):
    """Standard data table slide (used for progress status and metrics)."""
    slide = blank_slide(prs)
    add_header(slide, title, kicker)

    n_rows, n_cols = len(rows) + 1, len(headers)
    table_w, table_h = Inches(11.9), Inches(0.5 * n_rows if 0.5 * n_rows < 5.3 else 5.3)
    x, y = Inches(0.7), Inches(1.65)

    gframe = slide.shapes.add_table(n_rows, n_cols, x, y, table_w, table_h)
    table = gframe.table

    if col_widths_in:
        for i, w in enumerate(col_widths_in):
            table.columns[i].width = Inches(w)

    for c, header in enumerate(headers):
        cell = table.cell(0, c)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        para = cell.text_frame.paragraphs[0]
        para.font.bold = True
        para.font.size = Pt(13)
        para.font.color.rgb = WHITE
        para.font.name = FONT

    status_colors = {
        "Done": GREEN,
        "In progress": AMBER,
        "Upcoming": GRAY,
        "Not started": GRAY,
    }
    for r, row in enumerate(rows, start=1):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.text = value
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if r % 2 else LIGHT_BG
            para = cell.text_frame.paragraphs[0]
            para.font.size = Pt(12.5)
            para.font.name = FONT
            para.font.color.rgb = status_colors.get(value, TEXT_DARK) if value in status_colors else TEXT_DARK
            if value in status_colors:
                para.font.bold = True

    add_footer(slide, slide_num)
    return slide


def add_timeline_slide(prs, slide_num, title, phases, kicker=""):
    """
    Horizontal timeline diagram. `phases` is a list of (label, status) where
    status in {"Done", "In progress", "Upcoming"} controls the marker color.
    """
    slide = blank_slide(prs)
    add_header(slide, title, kicker)

    status_color = {"Done": GREEN, "In progress": AMBER, "Upcoming": GRAY}
    n = len(phases)
    margin = 0.9
    usable_w = 13.333 - 2 * margin
    line_y = 3.3

    line = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(margin), Inches(line_y), Inches(margin + usable_w), Inches(line_y)
    )
    line.line.color.rgb = GRAY
    line.line.width = Pt(2)

    step = usable_w / (n - 1) if n > 1 else 0
    for i, (label, status) in enumerate(phases):
        cx = margin + i * step
        marker = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(cx - 0.18), Inches(line_y - 0.18), Inches(0.36), Inches(0.36)
        )
        marker.fill.solid()
        marker.fill.fore_color.rgb = status_color[status]
        marker.line.color.rgb = WHITE
        marker.line.width = Pt(1.5)
        marker.shadow.inherit = False

        lbl = slide.shapes.add_textbox(Inches(cx - 1.0), Inches(line_y + 0.35), Inches(2.0), Inches(0.9))
        tf = lbl.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = label
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        p.font.name = FONT
        p.alignment = PP_ALIGN.CENTER

        stat = slide.shapes.add_textbox(Inches(cx - 1.0), Inches(line_y - 0.75), Inches(2.0), Inches(0.35))
        sp = stat.text_frame.paragraphs[0]
        sp.text = status
        sp.font.size = Pt(11)
        sp.font.bold = True
        sp.font.color.rgb = status_color[status]
        sp.font.name = FONT
        sp.alignment = PP_ALIGN.CENTER

    legend = slide.shapes.add_textbox(Inches(0.9), Inches(5.9), Inches(11.5), Inches(0.4))
    lp = legend.text_frame.paragraphs[0]
    lp.text = "Green = done      Amber = in progress      Gray = upcoming"
    lp.font.size = Pt(12)
    lp.font.color.rgb = TEXT_DARK
    lp.font.name = FONT

    add_footer(slide, slide_num)
    return slide


def add_closing_slide(prs, title, lines):
    slide = blank_slide(prs)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    bg.shadow.inherit = False

    tb = slide.shapes.add_textbox(Inches(0.9), Inches(2.9), Inches(11.5), Inches(1.0))
    p = tb.text_frame.paragraphs[0]
    p.text = title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT

    mb = slide.shapes.add_textbox(Inches(0.9), Inches(4.0), Inches(11.5), Inches(2.0))
    tf = mb.text_frame
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(16)
        p.font.color.rgb = RGBColor(0xC9, 0xD6, 0xE8)
        p.font.name = FONT
        p.space_after = Pt(6)
    return slide


# ── Content ───────────────────────────────────────────────────────────────

def build():
    prs = new_presentation()
    n = 1  # running slide counter for footers, incremented after each add_*_slide call

    add_title_slide(
        prs,
        title="Comparative Study of Fine-Tuning, RAG, and Hybrid Models\nfor Code Completion in Enterprise Repositories",
        subtitle="Mid-Term Progress Update",
        meta_lines=[
            "Nidwija Bhatta",
            "nidwija.bhatta@cotiviti.com",
            "September 2026",
        ],
    )
    n += 1

    add_bullet_slide(prs, n, "Agenda", [
        ("Problem and motivation", 0),
        ("Research questions", 0),
        ("Proposed system overview", 0),
        ("Datasets and data pipeline", 0),
        ("Implementation progress so far", 0),
        ("Evaluation plan", 0),
        ("Timeline and next steps", 0),
    ], kicker="Overview")
    n += 1

    add_bullet_slide(prs, n, "Problem and Motivation", [
        ("Modern code completion models perform well on general programming tasks", 0),
        ("They struggle inside enterprise repositories that depend on internal APIs, cross file references, and shared utility modules", 0),
        ("Benchmarks such as RepoBench and CrossCodeEval show that multi file completion is still hard even for strong pretrained code models", 0),
        ("Enterprise teams need completion systems that understand their own codebase, not just general syntax and public library usage", 0),
        ("This project studies whether combining retrieval with model adaptation closes that gap", 0),
    ], kicker="Motivation")
    n += 1

    add_bullet_slide(prs, n, "Research Questions", [
        ("RQ1", 0),
        ("Does repository level retrieval improve completion accuracy compared to standalone fine tuning", 1),
        ("RQ2", 0),
        ("Does fine tuning improve how well a model uses retrieved context", 1),
        ("RQ3", 0),
        ("Does a hybrid approach outperform both individual baselines", 1),
        ("RQ4", 0),
        ("What retrieval strategy best supports enterprise repository completion", 1),
    ], kicker="Research Questions")
    n += 1

    add_three_box_slide(prs, n, "Three Systems Under Comparison", [
        ("RAG Only", [
            "Retrieval context injected into a frozen code language model",
            "No training involved",
            "Baseline for retrieval alone",
        ], False),
        ("Fine-Tuning Only", [
            "Project adapted model using QLoRA",
            "No retrieval at inference time",
            "Baseline for adaptation alone",
        ], False),
        ("Hybrid", [
            "Retrieved context fed into the fine tuned model",
            "Combines adaptation with retrieval",
            "Main contribution of this thesis",
        ], True),
    ], kicker="System Design")
    n += 1

    add_diagram_slide(
        prs, n, "Baseline 1: RAG Only Pipeline",
        labels=["Repository", "Code Chunking", "Embeddings", "Vector Database", "Retriever", "LLM", "Completion"],
        highlight_idx=None,
        caption_bullets=[
            "The base language model stays frozen, nothing is trained in this baseline",
            "Retrieval brings in relevant code snippets from the repository at inference time",
            "Embedding model used is microsoft unixcoder base, a code specific embedding model",
            "Vector search is done with FAISS using cosine similarity",
        ],
        kicker="Architecture",
    )
    n += 1

    add_diagram_slide(
        prs, n, "Baseline 2: Fine-Tuning Only Pipeline",
        labels=["Repository Examples", "Training Pair Creation", "Fine-Tuning Dataset", "Model Fine-Tuning", "Project-Adapted Model", "Completion"],
        highlight_idx=None,
        caption_bullets=[
            "No retrieval happens at inference time in this baseline",
            "The model learns repository specific patterns directly through training",
            "Uses QLoRA, four bit quantization combined with low rank adapters, which is memory efficient",
            "Same base model, Qwen2.5-Coder-1.5B, as the other two systems for a fair comparison",
        ],
        kicker="Architecture",
    )
    n += 1

    add_diagram_slide(
        prs, n, "Proposed System: Hybrid RAG + Fine-Tuning",
        labels=["Repository", "Retriever", "Relevant Code Context", "Fine-Tuned Model", "Completion"],
        highlight_idx=3,
        caption_bullets=[
            "Combines dynamic retrieval with a model that is already adapted to the project",
            "This is the core contribution of the thesis",
            "Uses the same base model and the same memory budget as both baselines, so any difference in results comes from the architecture, not from a bigger model",
        ],
        kicker="Architecture",
    )
    n += 1

    add_bullet_slide(prs, n, "Datasets", [
        ("RepoBench, Python v1.1", 0),
        ("Full repositories with cross file completion tasks and retrieval benchmarks", 1),
        ("CrossCodeEval", 0),
        ("Cross file dependency tasks that include ground truth relevant files", 1),
        ("The same two datasets are used across all three systems for a fair, apples to apples comparison", 0),
        ("These are not used as a typical single train and test split", 0),
        ("Both datasets are converted into one shared format and then used for training, for building the retrieval index, and for the final test set", 1),
    ], kicker="Data")
    n += 1

    add_diagram_slide(
        prs, n, "Data Preparation Pipeline",
        labels=["RepoBench", "CrossCodeEval", "Preprocessing Script", "Unified Format", "Train / Val / Test"],
        highlight_idx=None,
        caption_bullets=[
            "Preprocessing converts both datasets into one format: input, output, and relevant files",
            "Examples are grouped by repository before splitting, so no repository appears in both the training set and the test set",
            "The same unified format lets identical evaluation code run on all three systems without special cases",
        ],
        kicker="Data",
    )
    n += 1

    add_table_slide(
        prs, n, "Evaluation Metrics",
        headers=["Category", "Metric", "What it measures"],
        rows=[
            ["Completion quality", "Exact Match", "Prediction equals ground truth exactly"],
            ["Completion quality", "Edit Similarity", "Levenshtein distance based similarity"],
            ["Completion quality", "Identifier Accuracy", "Correct function, class, and variable names"],
            ["Completion quality", "CodeBLEU", "Blends n-gram, syntax, and semantic similarity"],
            ["Retrieval quality", "Precision at K / Recall at K", "How many retrieved files are actually relevant"],
            ["Retrieval quality", "Mean Reciprocal Rank", "How high the first relevant file is ranked"],
            ["Efficiency", "Latency and memory", "Retrieval time, inference time, GPU and CPU usage"],
        ],
        col_widths_in=[2.6, 3.0, 6.3],
        kicker="Evaluation",
    )
    n += 1

    add_table_slide(
        prs, n, "Implementation Progress",
        headers=["Component", "Status"],
        rows=[
            ["Project setup and configuration", "Done"],
            ["Code chunking for retrieval", "Done"],
            ["Code embedding and FAISS vector store", "Done"],
            ["Retriever (query to context)", "Done"],
            ["Fine-tuning trainer (QLoRA)", "Done"],
            ["Hybrid inference pipeline", "Done"],
            ["Evaluation metrics and comparison report", "Done"],
            ["Dataset download scripts", "Done"],
            ["Dataset preprocessing script", "Done"],
            ["Running full training and generating results", "In progress"],
        ],
        col_widths_in=[8.5, 3.4],
        kicker="Status",
    )
    n += 1

    add_bullet_slide(prs, n, "What Has Actually Been Built", [
        ("A full data pipeline that downloads, cleans, and converts two different public datasets into one shared format", 0),
        ("A retrieval system covering chunking, code specific embeddings, and FAISS vector search", 0),
        ("A fine-tuning system using QLoRA to adapt a code language model to a specific repository", 0),
        ("A hybrid architecture that fuses retrieval with a project adapted model", 0),
        ("An evaluation framework covering multiple metrics, latency and memory tracking, and automatic report generation", 0),
        ("The remaining work is running these systems at scale and analyzing the numbers they produce, not simply reading someone else's results", 0),
    ], kicker="Contribution")
    n += 1

    add_timeline_slide(prs, n, "Project Timeline", [
        ("Literature Review", "Done"),
        ("Dataset Preparation", "Done"),
        ("RAG Baseline", "Done"),
        ("Fine-Tuning Baseline", "Done"),
        ("Hybrid System", "Done"),
        ("Evaluation and Results", "In progress"),
        ("Thesis Writeup", "Upcoming"),
    ], kicker="Schedule")
    n += 1

    add_bullet_slide(prs, n, "Risks and Mitigations", [
        ("Limited GPU availability for fine tuning", 0),
        ("Mitigated by using a small 1.5 billion parameter model with four bit quantization", 1),
        ("Dataset schema differences between the official release and available mirrors", 0),
        ("Mitigated by a preprocessing script that normalizes both formats and warns on mismatch", 1),
        ("Risk that results look too close to prior published work", 0),
        ("Mitigated by comparing directly against published baselines and clearly stating what is different in this study", 1),
    ], kicker="Risk Management")
    n += 1

    add_bullet_slide(prs, n, "Next Steps", [
        ("Download RepoBench and CrossCodeEval and run the preprocessing script", 0),
        ("Build the retrieval index over the target repository", 0),
        ("Run fine tuning and save the adapted model", 0),
        ("Run the full three system comparison and collect metrics", 0),
        ("Compare results against published baselines from the literature", 0),
        ("Build comparison graphs and tables for the thesis defense", 0),
    ], kicker="What's Next")
    n += 1

    add_closing_slide(prs, "Thank You", [
        "Questions and discussion",
        "Nidwija Bhatta",
        "nidwija.bhatta@cotiviti.com",
    ])

    return prs


if __name__ == "__main__":
    from pathlib import Path
    out_path = Path(__file__).parent / "Midterm_Progress_Update.pptx"
    presentation = build()
    presentation.save(str(out_path))
    print(f"Saved deck to {out_path}")