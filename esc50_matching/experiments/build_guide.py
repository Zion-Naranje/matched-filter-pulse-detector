"""Build docs/project_guide.docx: explanation, viva answers, base paper notes and demo script with screenshots."""
import csv, json, re
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from common import FIG, ROOT, TAB

R = json.loads((TAB / "results.json").read_text())
DEMO = ROOT / "docs" / "demo"
OUT = ROOT / "docs" / "project_guide.docx"
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



sec.left_margin = sec.right_margin = Inches(0.8)
sec.top_margin = sec.bottom_margin = Inches(0.7)
doc.styles["Normal"].font.size = Pt(10)
doc.styles["Normal"].paragraph_format.space_after = Pt(4)
doc.styles["Normal"].paragraph_format.line_spacing = 1.05
for n, sz in (("Heading 1", 15), ("Heading 2", 12)):
    doc.styles[n].font.size = Pt(sz)
    doc.styles[n].paragraph_format.space_before = Pt(8)
    doc.styles[n].paragraph_format.space_after = Pt(3)


def demo(name, caption, width=6.3):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(1)
    p.add_run().add_picture(str(DEMO / name), width=Inches(width))
    para(caption, italic=True, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER)


best = list(csv.reader(open(TAB / "best_threshold.csv")))[1:]
cl = {r[1]: r for r in best if r[0] == "class"}
rp = {r[1]: r for r in best if r[0] == "repeat"}

para("Project Guide: Template Matching of Environmental Sounds", bold=True, size=18)
para("Template matching with normalised cross-correlation (NCC) on ESC-50  |  explanation, base paper, demo script and viva answers", italic=True, size=10)

doc.add_heading("1. The project in 60 seconds", 1)
para("**Question:** can a computer find a known sound inside a longer recording without training any model? **Method:** take one example of the sound (the template), slide it along the recording, and at every "
     "position compute the normalised cross-correlation (NCC), a score from -1 to 1 that says how closely that part of the recording has the same waveform shape as the template (1 = identical). Peaks above a threshold are "
     "detections. **Test:** I join ESC-50 clips with 1 s of silence between them, so I know exactly where every clip starts and ends, and I can mark each detection correct or false and compute precision, recall and F1.")
bullets([
    f"**If the same sound repeats** (even with random volume and noise at 20 dB SNR) it is found perfectly: F1 = 1.00 for all five classes (no false detections).",
    "**If it is a different recording of the same class** (another dog bark) raw-waveform NCC mostly fails: scores stay below about 0.15. Only dog and door_wood_knock clearly beat a chance baseline; rain and siren are at chance.",
    "**Conclusion:** NCC is a good, training-free detector for a sound that recurs identically (buzzers, alarms, a fixed clip) but it does not generalise across different recordings; that needs spectrogram features or learned few-shot models (the base paper's context).",
])

doc.add_heading("2. Concepts you should be able to explain", 1)
table(["Concept", "Plain meaning", "In this project"], [
    ["Template matching", "Find a known pattern by sliding it along the data and measuring similarity at each position.", "Template = one ESC-50 clip (first fold-1 clip of the class)."],
    ["Cross-correlation", "Sum of products of template and signal at each shift; large when they line up.", "Computed for all shifts at once with FFTs: IFFT(FFT(x)·conj(FFT(t))), zero-padded."],
    ["Normalisation", "Divide by the window energy and template energy so loudness does not matter; result in [-1, 1].", "Window energy from a running sum of x². Windows with almost no energy (silence) score 0."],
    ["Threshold + NMS", "Keep scores above a threshold; if two peaks are within one template length keep only the strongest.", "Slider 0.1-0.9; min separation = template length."],
    ["Ground truth", "The true positions of the sound, known because I built the recording.", "Start and end sample of every inserted clip."],
    ["Correct detection", "Detection centre (start + half template) lies inside a true occurrence not yet matched.", "Else false: other class, silence, or a duplicate in the same clip."],
    ["Precision / recall / F1", "Precision = TP/(TP+FP); recall = TP/(TP+FN); F1 = their harmonic mean.", "Low threshold: high recall, low precision. High threshold: the opposite."],
    ["Chance baseline", "Same detections with the score curve circularly shifted, so heights are kept but positions are random.", "Shows which F1 values mean real skill (they should clearly exceed it)."],
    ["Two test conditions", "'repeat': the template itself (gain 0.5-1.5, 20 dB noise). 'class': other clips of the same class.", "Easy vs hard; shows when NCC works and when it does not."],
    ["Preprocessing", "Mono, 44.1 kHz to 16 kHz, peak-normalise, trim ESC-50's silent padding.", "Padding would otherwise be part of the template and the 'clip'."],
], widths=[1.3, 3.0, 2.6], size=8.5)

doc.add_heading("3. How the code is organised", 1)
para("**src/dataset.py** reads clips from your ESC-50 zip, a folder, or downloads single files, and preprocesses them. **src/matching.py** has ncc() and pick_peaks(). **src/recording.py** joins clips and keeps the ground-truth spans. "
     "**src/metrics.py** labels detections and computes TP/FP/FN, precision, recall and F1. **app.py** is the Streamlit page. **experiments/exp_threshold.py** produced the results table and figures; **tests/** has 6 pytest tests "
     "(self-correlation is 1.0, an embedded template is found within one sample, silence scores 0, metrics on a toy case, data loading from zip and folder).")

doc.add_page_break() if False else None
doc.add_heading("4. Results to quote (real numbers from the experiment)", 1)
para(f"{R['setup']['n_recordings']} recordings per class and condition, each with 2 true occurrences (60 per class), thresholds 0.02-0.90 in steps of 0.02; best threshold = lowest threshold with the highest F1.", size=9, italic=True, keep=True)
rows = [[c, cl[c][4], cl[c][7], cl[c][13], rp[c][4], rp[c][7]] for c in cl]
table(["Class", "Hard: best thr.", "Hard: best F1", "Hard: chance F1", "Repeat: best thr.", "Repeat: best F1"], rows, widths=[1.4, 1.1, 1.1, 1.2, 1.2, 1.1], size=9)
para("Be ready to say: the hard-case F1 values for rooster (0.41 vs chance 0.34), rain (0.21 vs 0.21) and siren (0.49 vs 0.47) are not meaningfully above chance; the best thresholds there are below 0.1, outside the app's slider range.", size=9)

doc.add_heading("5. The base paper and how to talk about it", 1)
para("**Tutul, Buchem and Pinkwart, \"Algorithmic Accuracy as a Motivational Driver in Robot-Mediated Learning: A Comparative Study of Cross-Correlation and CNN-Based Sound Detection in an Interactive Quiz Game\", arXiv:2607.16299, July 2026** (open-access preprint, cs.HC).")
bullets([
    "**What it did (from its abstract/listing):** a Pepper humanoid robot ran a buzzer-based quiz. Two ways of detecting the buzzer sound were compared: a CNN and a cross-correlation detector that compares the incoming audio with a reference template recorded before each session and signals a detection when the normalised correlation coefficient exceeds a preset threshold. 40 university students were split 20/20. It reports that the cross-correlation version gave better motivational results, and a third-party summary mentions higher detection accuracy in the live classroom.",
    "**Why it is a good base for you:** it uses exactly your technique (NCC against a stored template with a threshold, no training).",
    "**How yours differs:** the paper studies learner motivation with one stereotyped buzzer sound. You evaluate the detector itself, with exact ground truth, precision/recall/F1 against threshold, five sound classes, and you show where it fails.",
    "**A good point to make:** a buzzer sounds almost identical each time, which is like your 'repeat' condition, where NCC is perfect; your 'class' condition shows what happens when sounds vary, which that setting avoids.",
    "**Be honest about its limits:** it is a preprint (not peer reviewed); I read only its abstract and listing, not the full text; a summary site noted its motivation claims rely on descriptive statistics. Open https://arxiv.org/abs/2607.16299 yourself before the viva and read the abstract and introduction.",
])
para("**Supporting papers (all 2020 or later):** Nolasco et al. 2023 (*Learning to detect an animal sound from five examples*): detecting a sound from a few examples; template matching is the traditional baseline and few-shot learning does better. Nolasco et al. 2022 (DCASE 2022 few-shot bioacoustic challenge). Gong et al. 2021 (AST, 95.6 % on ESC-50 as a learned classifier). Kong et al. 2020 (PANNs, pretrained audio networks).", size=9)

doc.add_heading("6. Demo script: what to set, what you will see, what to say", 1)
para("Start the app (`streamlit run app.py`). Either set the sliders as listed, or open each link in the browser (it presets the sliders). Use the sidebar: Template class = dog, Test recording = Generated mix, Random mix (seed) = 1, Other-class clips = 3.", size=9)
table(["#", "Settings", "Link (after the address http://localhost:8501/)", "Expected"], [
    ["1", "dog; repeat; threshold 0.30; occurrences 2", "?cls=dog&mode=repeat&thr=0.30&seed=1&npos=2&nneg=3", "P 1.00, R 1.00, F1 1.00; TP/FP/FN 2/0/0"],
    ["2", "dog; repeat; threshold 0.10; occurrences 3", "?cls=dog&mode=repeat&thr=0.10&seed=1&npos=3&nneg=3", "P 0.60, R 1.00, F1 0.75; 3/2/0"],
    ["3", "dog; other clips (hard); threshold 0.75; occurrences 3", "?cls=dog&mode=class&thr=0.75&seed=1&npos=3&nneg=3", "all 0; 0/0/3"],
    ["4", "dog; hard; threshold 0.10; occurrences 2", "?cls=dog&mode=class&thr=0.10&seed=1&npos=2&nneg=3", "P 0.17, R 0.50, F1 0.25; 1/5/1"],
    ["5", "dog; hard; threshold 0.14; occurrences 2", "?cls=dog&mode=class&thr=0.14&seed=1&npos=2&nneg=3", "P 1.00, R 0.50, F1 0.67; 1/0/1"],
], widths=[0.3, 1.9, 3.3, 1.4], size=8)
demo("demo1_easy.png", "Case 1 - the sound repeats: two sharp NCC spikes near 1.0 at the true positions, nothing else above the line. Say: 'when the sound recurs, NCC finds it perfectly, even at a different volume and with noise.'")
demo("demo2_low_threshold.png", "Case 2 - threshold too low (0.10): all 3 found (recall 1.00) but two red lines in loud rooster clips are false alarms (precision 0.60). Say: 'a low threshold trades precision for recall.' Now drag the slider up to 0.30 and F1 becomes 1.00.")
demo("demo3_high_threshold_hard.png", "Case 3 - different recordings of the same class, threshold 0.75: nothing is detected, all 3 occurrences are missed. The NCC curve never gets above about 0.2. Say: 'raw-waveform correlation does not recognise a different dog bark.'")
demo("demo4_hard_low_threshold.png", "Case 4 - same hard case with threshold 0.10: one true dog found but 5 false detections (red lines). Say: 'lowering the threshold finds a few, but mostly random peaks, which is why I added a chance baseline.'")
demo("demo5_hard_sweet_spot.png", "Case 5 - threshold 0.14 (just below the highest score, 0.14): one correct detection, no false ones, one missed (precision 1.00, recall 0.50). Say: 'there is a narrow sweet spot, but it is specific to this recording, not reliable.'")
para("Other things to try live: change the template class (siren and rain have 5 s templates and also reach 1.00 in the repeat condition), raise 'Other-class clips' to 6 to show more distractors, change the seed to get a different random order, or upload your own WAV (no ground truth, so only detections).", size=9)

doc.add_heading("7. Likely viva questions and short answers", 1)
qa = [
 ("What is NCC and why normalise?", "Correlation of the template with each window, divided by the energies of the template and that window. Without it a loud segment scores high just for being loud; with it the score is volume-independent and lies in [-1, 1], so one threshold works."),
 ("How do you compute it fast?", "One FFT-based correlation gives the numerator for all shifts (O(N log N) instead of O(N·M)); the window energy comes from a running (cumulative) sum of x²."),
 ("How do you know the right answers?", "I build the recording myself by joining clips with 1 s silences and store each clip's start and end sample."),
 ("When is a detection correct?", "If its centre (start + half the template length) lies inside a true occurrence not already matched. Detections in other clips, in silence, or a second one in an already matched clip are false."),
 ("What is non-maximum suppression?", "Among peaks closer than one template length, keep only the strongest, so one sound gives one detection."),
 ("Why does it fail on different dog barks?", "Correlation compares exact sample-by-sample waveform shape; two different barks differ in timing and phase, so scores stay below about 0.15. Spectrograms or learned features are needed."),
 ("Why a chance baseline?", "True clips cover much of each recording, so random detections often land in one and give a non-zero F1. Dog and door_wood_knock beat chance; rain and siren do not."),
 ("Why are the best thresholds below the slider's 0.1?", "Because the scores for different recordings are so low; at those thresholds the detector is close to picking arbitrary peaks. That is a finding, not a bug."),
 ("Precision vs recall?", "Lower the threshold: more detections, recall up, precision down (case 2). Raise it: the opposite (case 3). F1 balances them."),
 ("Why 16 kHz and trimming the padding?", "16 kHz keeps the correlation fast and keeps the sound content; ESC-50 pads short sounds with zeros, which would otherwise become part of the template and the true clip."),
 ("What is your base paper and how does it relate?", "Tutul et al., 2026 preprint: a normalised cross-correlation detector with a fixed threshold against a stored template, compared with a CNN. I use the same technique but evaluate it with ground truth and show when it works and when it fails."),
 ("What would you improve?", "Correlate spectrograms or learned embeddings (as in the few-shot work of Nolasco et al.), use several templates per class, test more templates and recordings, and add noise robustness tests."),
 ("What are the limits of your study?", "One fixed template per class, 30 recordings (60 true occurrences) per class, five classes, synthetic joins of clean clips, and a preprint as base paper."),
]
for i, (q, a_) in enumerate(qa, 1):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2)
    add_runs(p, f"**Q{i}. {q}**  {a_}", size=9)

doc.add_heading("8. Before you present", 1)
bullets([
    "Fill in your name, roll number, guide, department, institute and year in the report and slides (yellow placeholders), and read both files once.",
    "Open the base-paper link and check the title and authors; skim its abstract and introduction.",
    "Run the app once beforehand with your ESC-50 zip (Data source line must say 'zip file'); try the five cases above.",
    "Do not claim the detector recognises sound classes in general; say it finds repeated sounds and that different recordings need better features.",
    "The Piczak 2015 paper is cited only as the source of the dataset (older than 2020).",
], )
doc.save(OUT)
print("saved", OUT)
