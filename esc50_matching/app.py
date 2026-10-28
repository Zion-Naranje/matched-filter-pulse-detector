"""Template matching of environmental sounds with normalised cross-correlation (ESC-50).

Run:  streamlit run app.py
"""
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from scipy.io import wavfile

from src.dataset import CLASSES, SR, Esc50, preprocess
from src.matching import ncc
from src.metrics import counts, detect, label_detections, prf
from src.recording import build_recording, join_clips

BLUE, ORANGE, GREEN, GREY, RED = "#0072B2", "#D55E00", "#009E73", "#6b6b6b", "#CC3311"
st.set_page_config(page_title="Sound template matching", layout="wide")
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "font.size": 9})


@st.cache_resource(show_spinner="Opening ESC-50...")
def get_dataset(path):
    return Esc50(path or None)


@st.cache_data(show_spinner="Loading clips...")
def make_recording(path, cls, mode, seed, n_pos, n_neg):
    ds = get_dataset(path)
    tfile = ds.clips_of(cls, folds={1})[0]
    rec = build_recording(ds, cls, tfile, seed, n_pos=n_pos, n_neg=n_neg, mode=mode)
    return rec, ds.load(tfile), tfile


st.title("Finding a sound inside a recording: normalised cross-correlation")
st.write("Pick a **template** sound. The app slides it along a longer recording and, at every position, computes how well the "
         "recording matches the template (1.0 = identical shape, 0 = unrelated). Peaks above the threshold are detections; "
         "green shading marks where the template sound really is.")

def qp(name, default, cast=str):
    """Initial widget value from the page link (?cls=dog&thr=0.3 ...), so demo cases can be opened by link."""
    try:
        return cast(st.query_params.get(name, default))
    except (TypeError, ValueError):
        return default


with st.sidebar:
    st.header("Settings")
    path = st.text_input("ESC-50 zip or folder (optional)", value="", help="Path to ESC-50-master.zip or the extracted folder. "
                         "Empty = use ./data or download the few clips needed from GitHub.")
    try:
        ds = get_dataset(path.strip())
        st.caption("Data source: " + ds.source)
    except Exception as exc:
        st.error(str(exc))
        st.stop()
    cls = st.selectbox("Template class", CLASSES, index=CLASSES.index(qp("cls", "dog")) if qp("cls", "dog") in CLASSES else 0)
    src = st.radio("Test recording", ["Generated mix", "Upload WAV"])
    thr = st.slider("Correlation threshold", 0.1, 0.9, min(max(qp("thr", 0.3, float), 0.1), 0.9), 0.01)
    if src == "Generated mix":
        mode = st.radio("The sound to find occurs as", ["class", "repeat"], format_func=lambda m: {
            "class": "other clips of the same class (hard)", "repeat": "the template itself, noisier (easy)"}[m],
            index=0 if qp("mode", "class") == "class" else 1)
        seed = st.number_input("Random mix (seed)", 0, 9999, qp("seed", 1, int))
        n_pos = st.slider("Occurrences", 1, 4, qp("npos", 2, int))
        n_neg = st.slider("Other-class clips", 0, 6, qp("nneg", 3, int))

try:
    if src == "Generated mix":
        rec, template, tfile = make_recording(path.strip(), cls, mode, int(seed), n_pos, n_neg)
        signal, spans = rec.signal, rec.spans
    else:
        tfile = ds.clips_of(cls, folds={1})[0]
        template = ds.load(tfile)
        up = st.file_uploader("Recording (WAV)", type=["wav"])
        if up is None:
            st.info("Upload a WAV file to search it for the template (no ground truth, so no precision/recall).")
            st.stop()
        sr_in, x = wavfile.read(io.BytesIO(up.read()))
        signal, spans = preprocess(x, sr_in), []
except Exception as exc:
    st.error(f"Could not prepare the data: {exc}")
    st.stop()

score = ncc(signal, template)
from src.matching import pick_peaks  # noqa: E402
starts, vals = pick_peaks(score, thr, len(template))
rows, _ = label_detections(starts, vals, len(template), spans)
t_ax = np.arange(len(signal)) / SR

# ----------------------------------------------------------- metrics
if spans:
    tp, fp, fn = counts(rows, spans)
    p, r, f = prf(tp, fp, fn)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Precision", f"{p:.2f}", help="correct detections / all detections")
    c2.metric("Recall", f"{r:.2f}", help="true occurrences found / all true occurrences")
    c3.metric("F1", f"{f:.2f}")
    c4.metric("TP / FP / FN", f"{tp} / {fp} / {fn}")
    if src == "Generated mix" and mode == "class" and not len(starts):
        st.warning("No detections at this threshold. Different clips of the same class rarely correlate above 0.1 in raw waveform "
                   "shape - try a lower threshold or the 'template itself' option.")
else:
    st.info(f"{len(rows)} detection(s). Template = {tfile} ({len(template) / SR:.2f} s).")

# ----------------------------------------------------------- plots
fig, ax = plt.subplots(3, 1, figsize=(11, 7.4), gridspec_kw=dict(height_ratios=[1, 1.3, 1.1]))
tt = np.arange(len(template)) / SR
ax[0].plot(tt, template, color=BLUE, lw=0.5)
ax[0].set(title=f"Template: class '{cls}' ({tfile}, {len(template) / SR:.2f} s)", xlabel="time (s)", ylabel="amplitude")
ax[1].plot(t_ax, signal, color="#333", lw=0.4)
for s in spans:
    ax[1].axvspan(s.start / SR, s.end / SR, color=GREEN if s.positive else GREY, alpha=0.25)
    ax[1].text((s.start + s.end) / 2 / SR, 1.08, s.category, ha="center", fontsize=8, color=GREEN if s.positive else GREY)
for rw in rows:
    ax[1].axvline(rw["centre"] / SR, color=BLUE if rw["correct"] or not spans else RED, lw=1.8)
ax[1].set(ylim=(-1.2, 1.4), ylabel="amplitude", title="Test recording: green = true occurrence of the template sound, grey = other sounds; "
          "vertical lines = detections (blue correct, red false)")
sc_t = (np.arange(len(score)) + len(template) // 2) / SR     # plot each score at the window centre
ax[2].plot(sc_t, score, color=ORANGE, lw=0.8)
ax[2].axhline(thr, color="k", ls="--", lw=0.9, label=f"threshold {thr:.2f}")
ax[2].set(ylim=(-0.15, 1.05), xlabel="time (s)", ylabel="NCC score", title="Normalised cross-correlation (score at the centre of each window)")
ax[2].legend(loc="upper right")
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

st.subheader("Detections")
if rows:
    table = [{"time (s)": round(rw["centre"] / SR, 2), "score": round(rw["score"], 3),
              "result": ("n/a" if not spans else ("correct" if rw["correct"] else "false")),
              "landed in": (spans[rw["span"]].category if rw["span"] is not None else "silence") if spans else ""} for rw in rows]
    st.dataframe(table, hide_index=True, width="stretch")
else:
    st.write("No detections above the threshold.")
st.caption("A detection is *correct* if its centre (start + half the template length) lies inside a true occurrence that has not "
           "already been matched; a second detection in the same clip counts as false. Peaks closer than one template length are "
           "merged (non-maximum suppression).")
