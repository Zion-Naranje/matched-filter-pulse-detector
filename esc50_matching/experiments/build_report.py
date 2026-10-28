"""Build docs/report.docx for the ESC-50 template-matching project from real results."""
import csv, json, re, subprocess, sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from common import FIG, ROOT, TAB
from src.dataset import CLASSES, SR, Esc50

R = json.loads((TAB / "results.json").read_text())
OUT = ROOT / "docs" / "report.docx"
PAGES = json.loads((ROOT / "docs" / ".pages.json").read_text()) if (ROOT / "docs" / ".pages.json").exists() else {}
META = Esc50().meta()

REFS = {
 1: 'R. Tutul, I. Buchem and N. Pinkwart, "Algorithmic Accuracy as a Motivational Driver in Robot-Mediated Learning: A Comparative Study of Cross-Correlation and CNN-Based Sound Detection in an Interactive Quiz Game", arXiv:2607.16299, July 2026 (open-access preprint; BASE PAPER).',
 2: 'I. Nolasco, S. Singh, V. Morfi, V. Lostanlen, A. Strandburg-Peshkin, E. Vidana-Vila, L. Gill, H. Pamula, H. Whitehead, I. Kiskin, F. H. Jensen, J. Morford, M. G. Emmerson, E. Versace, E. Grout, H. Liu, B. Ghani and D. Stowell, "Learning to detect an animal sound from five examples", Ecological Informatics, vol. 77, art. 102258, 2023, doi:10.1016/j.ecoinf.2023.102258 (also arXiv:2305.13210).',
 3: 'I. Nolasco et al., "Few-shot bioacoustic event detection at the DCASE 2022 challenge", arXiv preprint, July 2022.',
 4: 'Y. Gong, Y.-A. Chung and J. Glass, "AST: Audio Spectrogram Transformer", Proc. Interspeech, 2021, arXiv:2104.01778.',
 5: 'Q. Kong, Y. Cao, T. Iqbal, Y. Wang, W. Wang and M. D. Plumbley, "PANNs: Large-Scale Pretrained Audio Neural Networks for Audio Pattern Recognition", IEEE/ACM Trans. Audio, Speech, and Language Processing, vol. 28, pp. 2880-2894, 2020, doi:10.1109/TASLP.2020.3030497.',
 6: 'K. J. Piczak, "ESC: Dataset for Environmental Sound Classification", Proc. 23rd ACM International Conference on Multimedia (ACM Multimedia), 2015 (cited only as the source of the dataset).',
 7: 'K. J. Piczak, ESC-50: Dataset for Environmental Sound Classification (2,000 clips, 50 classes), github.com/karolpiczak/ESC-50.',
 8: 'Creative Commons Attribution-NonCommercial 3.0 licence (CC BY-NC 3.0), creativecommons.org/licenses/by-nc/3.0/.',
 9: 'Freesound, the online sound database from which ESC-50 clips were extracted, freesound.org.',
 10: 'NumPy documentation, numpy.org/doc/.',
 11: 'SciPy documentation (scipy.io.wavfile, scipy.signal.resample_poly), docs.scipy.org/doc/scipy/.',
 12: 'Matplotlib documentation, matplotlib.org/stable/.',
 13: 'Streamlit documentation, docs.streamlit.io.',
 14: 'pytest documentation, docs.pytest.org.',
 15: 'python-docx documentation, python-docx.readthedocs.io.',
 16: 'python-pptx documentation, python-pptx.readthedocs.io.',
 17: 'Python standard library documentation (csv, zipfile, urllib), docs.python.org/3/library/.',
}
(ROOT / "docs" / "refs.json").write_text(json.dumps(REFS))


def csv_rows(name):
    with open(TAB / f"{name}.csv") as f:
        return list(csv.reader(f))


_out = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True).stdout
N_TESTS = re.search(r"(\d+) passed", _out).group(1)
FAILED = "failed" in _out

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
for m in ("left_margin", "right_margin"):
    setattr(sec, m, Inches(1.0))
sec.top_margin = sec.bottom_margin = Inches(0.9)
st = doc.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(11)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.12
for name, size in (("Heading 1", 18), ("Heading 2", 14), ("Heading 3", 12)):
    h = doc.styles[name]
    h.font.name, h.font.size, h.font.bold = "Calibri", Pt(size), True
    h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    h.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 10)
    h.paragraph_format.keep_with_next = True

fig_n = [0]
tab_n = [0]


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def para(text="", bold=False, italic=False, align=None, size=None, style=None, keep=False):
    p = doc.add_paragraph(style=style)
    add_runs(p, text, bold, italic, size)
    if align:
        p.alignment = align
    if keep:
        p.paragraph_format.keep_with_next = True
    return p


PLACE = re.compile(r"(\[(?:Student name|Roll no|Guide name|Department|Institute|Academic year|Base paper to be verified by the student|Year|Venue / DOI|Benefits|Future scope)\])")


def add_runs(p, text, bold=False, italic=False, size=None):
    """Text with **bold** segments; the six placeholders are highlighted yellow."""
    for seg in re.split(r"(\*\*.+?\*\*)", text):
        b = bold
        if seg.startswith("**") and seg.endswith("**"):
            seg, b = seg[2:-2], True
        for part in PLACE.split(seg):
            if not part:
                continue
            r = p.add_run(part)
            r.bold, r.italic = b, italic
            if size:
                r.font.size = Pt(size)
            if PLACE.fullmatch(part):
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW


def bullets(items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        add_runs(p, it)
        p.paragraph_format.space_after = Pt(2)


def numbered(items):
    for it in items:
        p = doc.add_paragraph(style="List Number")
        add_runs(p, it)
        p.paragraph_format.space_after = Pt(2)


def table(header, rows, widths=None, caption=None, size=9, align_num=True):
    if caption:
        tab_n[0] += 1
        para(f"Table {tab_n[0]}: {caption}", bold=True, size=10, keep=True)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size = True, Pt(size)
        shade(c, "DCE6F2")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], str(v), size=size)
            cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
    # repeat header row, keep rows from splitting
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "true")
        trPr.append(cs)
    if widths:
        t.autofit = False
        for i, w in enumerate(widths):
            t.columns[i].width = Inches(w)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    if len(rows) <= 8:                       # keep short tables on one page
        for row in t.rows[:-1]:
            for c in row.cells:
                for pp in c.paragraphs:
                    pp.paragraph_format.keep_with_next = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figure(name, caption, width=6.3):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG / name), width=Inches(width))
    fig_n[0] += 1
    c = para(f"Figure {fig_n[0]}: {caption}", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)


def h1(text, page_break=True):
    if page_break:
        doc.add_page_break()
    doc.add_heading(text, 1)


# ---------------------------------------------------------------- footer page numbers
def add_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)
    run.font.size = Pt(9)


add_page_number(sec)


# ================================================================ COVER
for _ in range(4):
    para()
para("Digital Signal Processing Project Report", size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Template Matching of Environmental Sounds using Normalised Cross-Correlation", bold=True, size=24, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Finding where a known sound occurs in a longer recording, scored against known ground truth (ESC-50)", italic=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(3):
    para()
for label in ("Student name", "Roll no", "Guide name", "Department", "Institute", "Academic year"):
    para(f"{label}: [{label}]", size=13, align=WD_ALIGN_PARAGRAPH.CENTER)

# ================================================================ INDEX
doc.add_page_break()
doc.add_heading("Index", 1)
INDEX = ["1  Introduction", "2  Comparative Study of Literature", "3  Objective", "4  Methodology", "5  Work Done", "6  Results", "7  References"]
for it in INDEX:
    p = doc.add_paragraph()
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.2), alignment=2, leader=1)
    add_runs(p, f"{it}\t{PAGES.get(it, '')}")
    p.paragraph_format.space_after = Pt(4)

# ================================================================ 1
h1("1  Introduction")
doc.add_heading("1.1  Background", 2)
para("Many sounds worth detecting, a door knock, a siren, a dog bark, have a characteristic waveform. If one example of the sound is known, "
     "a simple way to find it in a longer recording is template matching: slide the template along the recording and measure at every position how "
     "similar the two are. The similarity measure used here is normalised cross-correlation (NCC). Plain cross-correlation grows with loudness; dividing by the energy "
     "of the template and of the current window of the recording makes the score independent of volume and bounded by 1, so a single threshold can be used. Template matching by correlation is a simple baseline for detecting a known sound from few examples [2], [1].")
para("To score such a detector honestly the true positions must be known. This project builds test recordings by joining clips from the ESC-50 dataset [6], [7] with silences "
     "between them, so the exact start and end of every clip is known and each detection can be marked correct or false.")
doc.add_heading("1.2  Dataset and key figures", 2)
cats = {r["category"] for r in META}
folds = sorted({int(r["fold"]) for r in META})
per_class = {c: sum(r["category"] == c for r in META) for c in CLASSES}
table(["Quantity", "Value", "Source"], [
    ["Clips in ESC-50", f"{len(META)}", "Counted from meta/esc50.csv [7]"],
    ["Classes", f"{len(cats)}", "Counted from meta/esc50.csv [7]"],
    ["Clips per class (chosen classes)", ", ".join(f"{c}: {n}" for c, n in per_class.items()), "Counted from meta/esc50.csv [7]"],
    ["Cross-validation folds", f"{len(folds)} (folds {folds[0]}-{folds[-1]})", "meta/esc50.csv [7]"],
    ["Clip length / original sample rate", "5 s / 44.1 kHz WAV", "Dataset description [6], [7]"],
    ["Rate used in this project", f"{SR} Hz (resampled)", "Chosen to keep correlation fast"],
    ["Classes used", ", ".join(CLASSES), "Chosen from the 50 class names in the CSV [7]"],
    ["Test recordings per class and condition", f"{R['setup']['n_recordings']}", "This project (Section 6)"],
    ["Licence of the data", "CC BY-NC 3.0 (non-commercial, attribution)", "[8]; clips originate from Freesound [9]"],
], widths=[2.2, 2.4, 1.9], caption="Dataset facts (counted from the metadata file) and the setup of this project. No external usage statistics are claimed.")
para("The data are used under the CC BY-NC 3.0 licence [8] for this non-commercial college project, with attribution to Piczak [6], [7].")

# ================================================================ 2
h1("2  Comparative Study of Literature")
para("Base paper: Tutul, Buchem and Pinkwart [1] (arXiv:2607.16299, July 2026), an open-access preprint (title, authors, arXiv number and date checked against its arXiv listing; "
     "its content is summarised from its abstract and listing only, the full text was not read, and as a preprint it is not peer reviewed). "
     "All other papers are from 2020 to 2023, so none is newer than the base paper; they are listed from latest to oldest and are summarised from abstract-level descriptions, not full-text reviews. "
     "The dataset paper [6] appears in the references only as the source of the data and is not part of this comparison.", italic=True, size=10)
lit = [
    ["Algorithmic Accuracy as a Motivational Driver in Robot-Mediated Learning: cross-correlation vs CNN sound detection [1] (BASE PAPER)", "2026", "arXiv:2607.16299 (open-access preprint)",
     "Detects a stored sound in live audio with a normalised correlation coefficient compared against a fixed threshold (no training), and compares it with a CNN detector in a classroom quiz game; reports that the cross-correlation detector worked better in that setting.",
     "Detects one fixed, stereotyped sound and mainly studies learner motivation. This project measures precision, recall and F1 of NCC against known clip positions and shows where it fails (different recordings of one class)."],
    ["Learning to detect an animal sound from five examples [2]", "2023", "Ecological Informatics 77, 102258; arXiv:2305.13210",
     "Sound event detection from only a few examples of the target sound; uses spectrogram cross-correlation template matching as a traditional baseline and reports that few-shot learning outperforms such signal-processing detectors.",
     "Suggests the next step for this project: correlate spectrograms or learned embeddings instead of raw waveforms."],
    ["Few-shot bioacoustic event detection at the DCASE 2022 challenge [3]", "2022", "arXiv preprint (July 2022)",
     "Overview of a community challenge on detecting a target sound from a few labelled examples, with datasets, baselines and submitted systems (the strongest used prototypical networks and transductive learning).",
     "Shows few-shot detection is still open; this project covers only the simplest one-template case."],
    ["AST: Audio Spectrogram Transformer [4]", "2021", "Interspeech 2021; arXiv:2104.01778",
     "A purely attention-based classifier on spectrograms that reports 95.6 % accuracy on ESC-50, the dataset used here.",
     "Needs labelled training data and classifies whole clips; it does not locate a sound inside a long recording."],
    ["PANNs: Large-Scale Pretrained Audio Neural Networks for Audio Pattern Recognition [5]", "2020", "IEEE/ACM TASLP 28, 2880-2894",
     "Networks pretrained on a large audio collection and transferred to other audio tasks, showing that learned features beat hand-crafted ones on many tasks.",
     "Pretraining needs large data and compute; this project is a training-free baseline."],
]
table(["Title", "Year", "Source", "Benefits", "Future scope"], lit, widths=[1.5, 0.45, 0.95, 2.1, 1.5], size=8,
      caption="Comparative study (base paper first; then latest to oldest; all from 2020 or later).")


# ================================================================ 3
h1("3  Objective")
bullets([
    "Load ESC-50 clips, convert to mono, resample to 16 kHz, normalise the amplitude.",
    "Build test recordings by joining clips with 1 s silences, recording the exact start and end of every clip as ground truth.",
    "Implement template matching with FFT-based normalised cross-correlation in NumPy, and peak picking with non-maximum suppression.",
    "Match detections to ground truth by the centre-in-span rule and compute precision, recall and F1.",
    "Provide a Streamlit app: template class, test recording, threshold slider, plot with true spans and detections, table, metrics.",
    "Measure precision, recall and F1 against threshold for five classes over at least 20 recordings each, and report the best threshold per class honestly.",
])

# ================================================================ 4
h1("4  Methodology")
figure("fig_flow.png", "Flow chart of the system.")
doc.add_heading("4.1  Preprocessing", 2)
para("Each clip is converted to mono, resampled from 44.1 kHz to 16 kHz with a polyphase filter [11], scaled so that its peak is 1, and stripped of the digital-silence padding ESC-50 adds to short events "
     "(samples below 0.1 % of the peak at the start and end are removed).")
doc.add_heading("4.2  Test recordings and ground truth", 2)
para("A recording joins five clips separated by 1 s of silence in a random order: two occurrences of the template sound and three clips of the other classes. The start and end sample of every clip is stored. "
     "Two conditions are used. In the **class** condition the occurrences are other clips of the template's class (folds 2-5; the template itself, from fold 1, is never in the recording). "
     "In the **repeat** condition the occurrences are the template clip itself with a random gain of 0.5-1.5 and white noise at 20 dB SNR, which tests the method when the sound recurs exactly.")
doc.add_heading("4.3  Normalised cross-correlation", 2)
para("For template t of length m and recording x, the score at lag k is  c[k] = sum_n x[k+n] t[n] / ( sqrt(sum_n x[k+n]^2) x sqrt(sum_n t[n]^2) ). The numerator for all lags is one FFT-based correlation "
     "(zero-padded, so linear), IFFT( FFT(x) x conj(FFT(t)) ) [10]. The window energy in the denominator is a difference of a running sum of x^2. The score lies in [-1, 1]; "
     "1 means the window is a scaled copy of the template. Windows with almost no energy (silence) are given score 0 so that quiet gaps cannot score highly.")
doc.add_heading("4.4  Detection and scoring", 2)
para("Local maxima of the score above the threshold are candidates. Non-maximum suppression keeps the strongest and discards any peak closer than one template length to a kept one. "
     "The detection time is the centre of the window (start + half the template length). A detection is **correct** if its centre lies inside a true occurrence not already matched; any other "
     "detection (in another class's clip, in silence, or a second one in an already matched clip) is **false**. TP, FP and FN are summed over the recordings, then precision = TP/(TP+FP), "
     "recall = TP/(TP+FN), F1 = 2PR/(P+R) (0 when a denominator is 0). A **chance baseline** repeats the detection on the score curve circularly shifted by a random amount, which keeps the peak heights "
     "but destroys their positions.")

# ================================================================ 5
h1("5  Work Done")
doc.add_heading("5.1  Tools", 2)
table(["Tool", "Used for", "Ref."], [
    ["Python 3 (csv, zipfile, urllib)", "Metadata, reading clips from the zip or folder, downloading single files", "[17]"],
    ["NumPy", "FFT correlation, running energy, peak picking, all core DSP", "[10]"],
    ["SciPy", "WAV reading and polyphase resampling only (no matched-filter or correlation routines)", "[11]"],
    ["Matplotlib", "Figures", "[12]"],
    ["Streamlit", "Interactive app", "[13]"],
    ["pytest", "Tests", "[14]"],
    ["python-docx / python-pptx", "This report and the slides", "[15], [16]"],
], widths=[1.9, 3.9, 0.7], caption="Tools used.")
doc.add_heading("5.2  Implementation steps", 2)
numbered([
    "src/dataset.py: reads clips from a local zip, an extracted folder, or (fallback) downloads only the needed files from GitHub; preprocessing as in Section 4.1.",
    "src/matching.py: ncc() and pick_peaks().",
    "src/recording.py: joins clips and stores the ground-truth spans, for the class and repeat conditions.",
    "src/metrics.py: detection, centre-in-span labelling, TP/FP/FN, precision/recall/F1.",
    "app.py: the Streamlit app (Figure 2).",
    f"tests/: {N_TESTS} pytest tests (self-correlation, embedded template, silence, metrics on a toy case, data loading from zip and folder).",
    "experiments/exp_threshold.py: the experiment of Section 6; writes docs/figures and docs/tables.",
])
figure("../screenshots/app_repeat.png", "The Streamlit app: template 'dog', two true occurrences found, precision, recall and F1 all 1.00 in the repeat condition.", width=4.3)

# ================================================================ 6
h1("6  Results")
st_ = R["setup"]
para(f"Five classes ({', '.join(CLASSES)}), {st_['n_recordings']} recordings per class and condition (each with 2 occurrences, so {2 * st_['n_recordings']} true occurrences per class), "
     "thresholds 0.02 to 0.90 in steps of 0.02. The template for each class is the first fold-1 clip. All numbers come from experiments/exp_threshold.py.", italic=True, size=10)
doc.add_heading("6.1  Repeat condition: the same sound recurs", 2)
figure("fig_prf_repeat.png", "Precision, recall and F1 against threshold when the occurrence is the template itself (gain 0.5-1.5, 20 dB noise).", 6.5)
doc.add_heading("6.2  Class condition: other clips of the same class", 2)
figure("fig_prf_class.png", "The same curves when the occurrences are other clips of the template's class. The dashed line is the chance baseline.", 6.5)
best = csv_rows("best_threshold")
hdr = ["Condition", "Class", "Template (s)", "Best thr.", "Precision", "Recall", "F1", "TP/FP/FN", "Chance F1"]
rows = [[r[0], r[1], r[3], r[4], r[5], r[6], r[7], f"{r[8]}/{r[9]}/{r[10]}", r[13]] for r in best[1:]]
table(hdr, rows, widths=[0.7, 1.15, 0.7, 0.65, 0.75, 0.6, 0.55, 0.9, 0.7], size=8,
      caption="Best threshold per class (the lowest threshold that maximises F1) and the results there.")
doc.add_heading("6.3  Why: scores of true and other clips", 2)
figure("fig_score_hist.png", "Highest NCC score reached inside each clip, for true occurrences and other-class clips (all five classes together).", 6.2)
figure("fig_example.png", "Examples. Top two panels: a repeat of the 'dog' template; the true occurrences score near 1. Bottom two: other 'dog' clips; every score stays below about 0.15.", 6.2)
cl = {r["class"]: r for r in R["best"] if r["mode"] == "class"}
rp = {r["class"]: r for r in R["best"] if r["mode"] == "repeat"}
rng_txt = ", ".join(f"{r[1]} {r[14]}" for r in best[1:] if r[0] == "repeat")
doc.add_heading("6.4  Points to note", 2)
bullets([
    f"**Exact repeats are found perfectly.** In the repeat condition every class reaches F1 = {min(float(r['F1']) for r in rp.values()):.3f} (all {2 * st_['n_recordings']} occurrences found, no false detections) at its best threshold; "
    f"the range of thresholds that gives this best F1 is: {rng_txt}. True occurrences reach a mean highest score of {float(rp['dog']['mean_pos']):.3f}, other-class clips {float(rp['dog']['mean_neg']):.3f} (dog).",
    f"**Different clips of the same class are mostly not found.** Raw-waveform NCC compares sample-by-sample shape, so two different dog barks, or two rain clips, correlate weakly (the mean highest score inside true clips is only "
    f"{min(float(r['mean_pos']) for r in cl.values()):.3f}-{max(float(r['mean_pos']) for r in cl.values()):.3f}). The best F1 values are "
    + ", ".join(f"{c} {float(cl[c]['F1']):.2f} (chance {float(cl[c]['chance_F1']):.2f})" for c in CLASSES) + ".",
    "**Only some of these are above chance.** Dog and door_wood_knock clearly beat the chance baseline; rooster is slightly above; rain and siren are at chance level, so no skill is claimed for them. "
    "Part of the apparent F1 comes from the fact that true clips cover a large share of the recording, so even random detections often land in one.",
    "**The best thresholds are very low** (0.02-0.14 in the class condition), partly below the 0.1-0.9 range of the app's slider; at such thresholds the detector is close to picking arbitrary peaks. A large threshold gives zero recall for different instances.",
    "Scores of true and other-class clips overlap strongly (Section 6.3), so a better representation (for example spectrogram features or learned few-shot models, as in [2], [3]) would be needed to recognise a class from one example; that is outside this project's scope.",
    "The template choice is fixed (first fold-1 clip per class) and there are 30 recordings per class (60 true occurrences), so the numbers carry sampling uncertainty; a different template could give different class-condition results.",
    "The centre-in-span rule matters: a template longer than the true clip can place the window centre outside the clip.",
    f"The pytest suite has {N_TESTS} tests and {'some failed' if FAILED else 'all pass'}. The app was run without errors.",
])

# ================================================================ 7
h1("7  References")
for n, text in REFS.items():
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.first_line_indent = Inches(-0.4)
    add_runs(p, f"[{n}]\t{text}", size=10)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.4))

doc.save(OUT)
print("saved", OUT)
ref_start = [i for i, p in enumerate(doc.paragraphs) if p.text.strip() == "7  References"][-1]
bodytxt = "\n".join(p.text for p in doc.paragraphs[:ref_start]) + "\n" + "\n".join(c.text for t in doc.tables for row in t.rows for c in row.cells)
cited = {int(n) for grp in re.findall(r"\[(\d+(?:\s*[,-]\s*\d+)*)\]", bodytxt) for n in re.findall(r"\d+", grp)}
print("references:", len(REFS), "| not cited:", [n for n in REFS if n not in cited])
