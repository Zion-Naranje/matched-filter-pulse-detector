"""Precision / recall / F1 against threshold for each template class (30 recordings per class and mode)."""
import numpy as np

from common import BLUE, GREEN, GREY, ORANGE, RED, plt, save_fig, update_results, write_table
from src.dataset import CLASSES, SR, Esc50
from src.matching import ncc, pick_peaks
from src.metrics import counts, label_detections, prf
from src.recording import build_recording

N_REC = 30
THR = np.round(np.arange(0.02, 0.901, 0.02), 2)
ds = Esc50()
print("source:", ds.source)
ds.prefetch(CLASSES)

res, best_rows, hist = {}, [], {}
for mode in ("class", "repeat"):
    for cls in CLASSES:
        tfile = ds.clips_of(cls, folds={1})[0]
        t = ds.load(tfile)
        tp = np.zeros(len(THR), int); fp = np.zeros(len(THR), int); fn = np.zeros(len(THR), int)
        btp = np.zeros(len(THR), int); bfp = np.zeros(len(THR), int); bfn = np.zeros(len(THR), int)   # chance baseline
        brng = np.random.default_rng(7)
        pos_max, neg_max = [], []
        for seed in range(N_REC):
            rec = build_recording(ds, cls, tfile, seed=1000 * (mode == "repeat") + seed, mode=mode)
            score = ncc(rec.signal, t)
            centres = np.arange(len(score)) + len(t) // 2
            for s in rec.spans:                                   # best score reachable inside each clip
                m = (centres >= s.start) & (centres < s.end)
                (pos_max if s.positive else neg_max).append(float(score[m].max()) if m.any() else 0.0)
            shifted = np.roll(score, int(brng.integers(len(score))))   # same peaks, random positions
            for i, th in enumerate(THR):
                st2, v2 = pick_peaks(shifted, th, len(t))
                r2, _ = label_detections(st2, v2, len(t), rec.spans)
                a2, b2, c2 = counts(r2, rec.spans)
                btp[i] += a2; bfp[i] += b2; bfn[i] += c2
                st, v = pick_peaks(score, th, len(t))
                rows, _ = label_detections(st, v, len(t), rec.spans)
                a, b, c = counts(rows, rec.spans)
                tp[i] += a; fp[i] += b; fn[i] += c
        P, R, F = zip(*[prf(a, b, c) for a, b, c in zip(tp, fp, fn)])
        j = int(np.argmax(F))                                      # first max = lowest threshold on ties
        ties = THR[np.isclose(F, F[j])]
        FB = [prf(a, b, c)[2] for a, b, c in zip(btp, bfp, bfn)]
        res[(mode, cls)] = dict(P=P, R=R, F=F, FB=FB, tp=tp, fp=fp, fn=fn)
        hist[(mode, cls)] = (pos_max, neg_max)
        best_rows.append([mode, cls, tfile, f"{len(t) / SR:.2f}", f"{THR[j]:.2f}", f"{P[j]:.3f}", f"{R[j]:.3f}", f"{F[j]:.3f}",
                          int(tp[j]), int(fp[j]), int(fn[j]), f"{np.mean(pos_max):.3f}", f"{np.mean(neg_max):.3f}", f"{FB[j]:.3f}", f"{ties.min():.2f}-{ties.max():.2f}"])
        print(best_rows[-1])
write_table("best_threshold", ["mode", "class", "template_clip", "template_s", "best_threshold", "precision", "recall", "F1",
                               "TP", "FP", "FN", "mean_max_score_true_clips", "mean_max_score_other_clips", "chance_F1_same_threshold", "thresholds_with_same_best_F1"], best_rows)
update_results("best", [dict(zip(["mode", "class", "template", "template_s", "thr", "P", "R", "F1", "TP", "FP", "FN",
                                  "mean_pos", "mean_neg", "chance_F1", "tie_range"], r)) for r in best_rows])
update_results("setup", dict(n_recordings=N_REC, thresholds=THR.tolist(), clips_per_recording="2 occurrences + 3 other-class clips",
                             gap_s=1.0, sr=SR, classes=CLASSES))

for mode, title in (("class", "Occurrences = other clips of the same class"), ("repeat", "Occurrences = the template sound itself (gain 0.5-1.5, 20 dB noise)")):
    fig, ax = plt.subplots(1, 5, figsize=(15, 3.2), sharey=True)
    for a, cls in zip(ax, CLASSES):
        r = res[(mode, cls)]
        a.plot(THR, r["P"], color=BLUE, label="precision"); a.plot(THR, r["R"], color=ORANGE, label="recall")
        a.plot(THR, r["F"], color=GREEN, lw=2.2, label="F1")
        a.plot(THR, r["FB"], color=GREY, ls="--", label="F1 by chance")
        a.set(title=cls, xlabel="threshold"); a.set_ylim(-0.02, 1.05)
    ax[0].set_ylabel("score"); ax[0].legend(fontsize=8)
    fig.suptitle(f"{title}  ({N_REC} recordings per class)", y=1.04, fontsize=11)
    save_fig(fig, f"fig_prf_{mode}.png")

fig, ax = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
for a, mode, ttl in zip(ax, ("class", "repeat"), ("Other clips of the class", "Template repeated")):
    pos = np.concatenate([hist[(mode, c)][0] for c in CLASSES]); neg = np.concatenate([hist[(mode, c)][1] for c in CLASSES])
    bins = np.linspace(0, 1, 41)
    a.hist(neg, bins, color=GREY, alpha=0.7, label="clips of other classes")
    a.hist(pos, bins, color=GREEN, alpha=0.8, label="true occurrences")
    a.set(title=ttl, xlabel="highest NCC score reached inside a clip", yscale="log")
ax[0].set_ylabel("number of clips"); ax[0].legend()
save_fig(fig, "fig_score_hist.png")

# example recording for the report: repeat mode, best threshold of that class; and class mode for contrast
import matplotlib.patches as mp
fig, axes = plt.subplots(4, 1, figsize=(11, 7.6), sharex=False)
for k, (mode, cls) in enumerate((("repeat", "dog"), ("class", "dog"))):
    tfile = ds.clips_of(cls, folds={1})[0]; t = ds.load(tfile)
    thr = float([r for r in best_rows if r[0] == mode and r[1] == cls][0][4]) if mode == "repeat" else 0.1
    thr = max(thr, 0.1)
    rec = build_recording(ds, cls, tfile, seed=3, mode=mode)
    score = ncc(rec.signal, t); st, v = pick_peaks(score, thr, len(t))
    rows, _ = label_detections(st, v, len(t), rec.spans)
    x = np.arange(len(rec.signal)) / SR
    a, b = axes[2 * k], axes[2 * k + 1]
    a.plot(x, rec.signal, color="#333", lw=0.4)
    for s in rec.spans:
        a.axvspan(s.start / SR, s.end / SR, color=GREEN if s.positive else GREY, alpha=0.25)
        a.text((s.start + s.end) / 2 / SR, 1.05, s.category, ha="center", fontsize=8, color=GREEN if s.positive else GREY)
    for r in rows:
        a.axvline(r["centre"] / SR, color=BLUE if r["correct"] else RED, lw=1.8)
    a.set(ylim=(-1.2, 1.35), title=f"{'Repeat of the template' if mode == 'repeat' else 'Other dog clips'}: green = true occurrence, grey = other class; "
          f"blue line = correct detection, red = false (threshold {thr:.2f})", ylabel="amplitude")
    b.plot(np.arange(len(score)) / SR, score, color=ORANGE, lw=0.8); b.axhline(thr, color="k", ls="--", lw=0.8)
    b.set(ylim=(-0.1, 1.05), ylabel="NCC", xlabel="time (s)" if k else "")
save_fig(fig, "fig_example.png")
