"""Build docs/presentation.pptx (8 slides) for the ESC-50 template-matching project."""
import json, re
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt
from common import FIG, ROOT, TAB

R = json.loads((TAB / "results.json").read_text())
REFS = {int(k): v for k, v in json.loads((ROOT / "docs" / "refs.json").read_text()).items()}
NAVY, BLUE, GREY, LIGHT = RGBColor(0x1F, 0x3A, 0x5F), RGBColor(0x00, 0x72, 0xB2), RGBColor(0x55, 0x55, 0x55), RGBColor(0xEE, 0xF3, 0xF8)
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
PLACE = re.compile(r"(\[(?:Student name|Roll no|Guide name|Department|Institute|Academic year|Base paper to be verified by the student)\])")


def runs(p, text, size, bold=False, color=None):
    for part in PLACE.split(text):
        if not part:
            continue
        r = p.add_run()
        r.text = part
        r.font.size, r.font.bold, r.font.name = Pt(size), bold, "Calibri"
        if color:
            r.font.color.rgb = color
        if PLACE.fullmatch(part):
            r.font.color.rgb = RGBColor(0, 0, 0)
            rPr = r._r.get_or_add_rPr()
            hl = etree.SubElement(rPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}highlight")
            etree.SubElement(hl, "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr").set("val", "FFFF00")


def box(slide, x, y, w, h, lines, size=18, bullet=False, color=None, bold=False, align=None, fill=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    if fill:
        tb.fill.solid()
        tb.fill.fore_color.rgb = fill
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        runs(p, ("•  " if bullet else "") + ln, size, bold, color)
        p.space_after = Pt(6)
        if align:
            p.alignment = align
    return tb


def title(slide, text, n):
    bar = slide.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.0))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    box(slide, 0.5, 0.15, 12, 0.7, [text], 30, color=RGBColor(255, 255, 255), bold=True)
    box(slide, 12.2, 7.0, 1, 0.4, [str(n)], 12, color=GREY, align=PP_ALIGN.RIGHT)


def pic(slide, name, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return slide.shapes.add_picture(str(FIG / name), Inches(x), Inches(y), **kw)



CL = {r["class"]: r for r in R["best"] if r["mode"] == "class"}
RP = {r["class"]: r for r in R["best"] if r["mode"] == "repeat"}
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
box(s, 0.8, 1.3, 11.7, 1.8, ["Template Matching of Environmental Sounds", "using Normalised Cross-Correlation"], 40, color=RGBColor(255, 255, 255), bold=True)
box(s, 0.8, 3.3, 11.7, 0.9, ["Finding where a known sound occurs in a longer recording (ESC-50)"], 22, color=RGBColor(0xCF, 0xDD, 0xEE))
box(s, 0.8, 4.5, 11.7, 2.6, ["Student name: [Student name]     Roll no: [Roll no]", "Guide name: [Guide name]",
                             "Department: [Department]     Institute: [Institute]", "Academic year: [Academic year]"], 18, color=RGBColor(255, 255, 255))

s = prs.slides.add_slide(BLANK); title(s, "1  Introduction", 2)
box(s, 0.5, 1.3, 7.0, 5.6, [
    "Goal: find where a known sound occurs in a longer recording",
    "Method: slide the template along the recording; score every position with normalised cross-correlation (NCC) [4], [7]",
    "Dividing by window and template energy makes the score volume-independent, in [-1, 1]",
    "Test data: ESC-50 [1], [2] clips joined with 1 s silences, so true positions are known",
    "ESC-50: 2,000 clips, 50 classes, 5 s, 44.1 kHz; CC BY-NC 3.0 [3]; we use 5 classes at 16 kHz",
], 18, bullet=True)
pic(s, "fig_example.png", 7.7, 1.4, w=5.3)

s = prs.slides.add_slide(BLANK); title(s, "2  Comparative Study of Literature", 3)
rows = [("Paper", "Year", "Takeaway"),
        ("[Base paper to be verified by the student]", "[Year]", "[Not verified within the time limit]"),
        ("Piczak, ESC dataset [1], [2]", "2015", "Labelled clips, 50 classes; benchmark data used here"),
        ("Richards, Fundamentals of Radar Signal Processing [4]", "2014", "Matched filter and correlation detection"),
        ("Richards, Scheer, Holm, Principles of Modern Radar [5]", "2010", "Correlation detection and thresholds"),
        ("Skolnik, Radar Handbook [6]", "2008", "Matched filtering reference"),
        ("TU Berlin, Matched Filter and Pulse Compression [7]", "n.d.", "FFT correlation in Python")]
tbl = s.shapes.add_table(len(rows), 3, Inches(0.5), Inches(1.4), Inches(12.3), Inches(4.4)).table
for j, w in enumerate((6.3, 1.3, 4.7)):
    tbl.columns[j].width = Inches(w)
for i, r in enumerate(rows):
    for j, t in enumerate(r):
        c = tbl.cell(i, j); c.text = ""
        runs(c.text_frame.paragraphs[0], t, 16, bold=(i == 0), color=RGBColor(255, 255, 255) if i == 0 else None)
        c.fill.solid(); c.fill.fore_color.rgb = NAVY if i == 0 else (LIGHT if i % 2 else RGBColor(255, 255, 255))
box(s, 0.5, 6.1, 12, 0.9, ["Base paper not verified (no access to check authors, year, venue, DOI) - left as a placeholder. Other rows are summaries, not full-text reviews."], 14, color=GREY)

s = prs.slides.add_slide(BLANK); title(s, "3  Objective", 4)
box(s, 0.6, 1.4, 12, 5.4, [
    "Load ESC-50, convert to mono 16 kHz, normalise",
    "Join clips with 1 s silences; record exact spans as ground truth",
    "FFT-based normalised cross-correlation in NumPy; threshold + non-maximum suppression",
    "Detection correct if its centre lies inside a true clip; precision, recall, F1",
    "Streamlit app with a threshold slider and plots",
    "Experiment: P/R/F1 vs threshold, 5 classes, 30 recordings each; best threshold per class",
], 22, bullet=True)

s = prs.slides.add_slide(BLANK); title(s, "4  Methodology", 5)
pic(s, "fig_flow.png", 0.4, 1.3, w=12.5)
box(s, 0.6, 5.2, 12, 1.8, ["score[k] = sum x[k+n]·t[n] / ( sqrt(sum x[k+n]²) · sqrt(sum t²) )   (numerator by FFT, window energy by running sum)",
                           "Two test conditions: other clips of the class  |  the template itself (gain 0.5–1.5, 20 dB noise)"], 17, bullet=True)

s = prs.slides.add_slide(BLANK); title(s, "5  Work Done", 6)
box(s, 0.5, 1.3, 5.8, 5.6, [
    "NumPy [8] for all matching; SciPy [9] only for WAV reading and resampling",
    "Data from your ESC-50 zip, a folder, or single-file GitHub download",
    "Streamlit app [11]; Matplotlib [10]",
    "pytest [12]: 6 tests, all pass",
    "Chance baseline added to judge the results honestly",
], 18, bullet=True)
pic(s, "../screenshots/app_repeat.png", 6.5, 1.3, h=5.4)

s = prs.slides.add_slide(BLANK); title(s, "6  Results", 7)
pic(s, "fig_prf_class.png", 0.3, 1.1, w=12.7)
box(s, 0.4, 4.2, 12.5, 3.1, [
    "Same sound repeated (gain 0.5–1.5, 20 dB noise): F1 = " + ", ".join(f"{c} {float(RP[c]['F1']):.2f}" for c in RP) + " (no false detections)",
    "Other clips of the class (figure): best F1 " + ", ".join(f"{c} {float(CL[c]['F1']):.2f} (chance {float(CL[c]['chance_F1']):.2f})" for c in CL),
    "Only dog and door_wood_knock clearly beat chance; rain and siren are at chance level",
    "Best thresholds are very low (0.02–0.14): raw-waveform NCC does not generalise across different recordings",
], 15, bullet=True)

s = prs.slides.add_slide(BLANK); title(s, "7  References", 8)
box(s, 0.5, 1.2, 12.4, 5.5, [f"[{n}] {REFS[n]}" for n in (1, 2, 3, 4, 5, 7)] + ["Base paper: [Base paper to be verified by the student]"], 14)
box(s, 0.5, 6.8, 12.4, 0.5, ["Full list of 16 references in the report."], 12, color=GREY)
prs.save(ROOT / "docs" / "presentation.pptx")
print("slides", len(prs.slides))
