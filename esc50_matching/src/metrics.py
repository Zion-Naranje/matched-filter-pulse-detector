"""Score detections against ground-truth spans: a detection is correct if its centre lies in a positive span."""
import numpy as np

from .matching import ncc, pick_peaks


def detect(rec, template, threshold, min_sep=None):
    """Run matching on a Recording. Returns (score_curve, starts, scores); min_sep defaults to the template length."""
    score = ncc(rec.signal, template)
    starts, vals = pick_peaks(score, threshold, min_sep or len(template))
    return score, starts, vals


def label_detections(starts, scores, template_len, spans):
    """One row per detection: centre (sample), score, correct?, index of the matched span.

    Strongest detections are matched first; each positive span can be matched once, so a second
    detection in an already-matched span counts as false (a duplicate).
    """
    rows, used = [], set()
    for i in np.argsort(-np.asarray(scores)):
        centre = starts[i] + template_len // 2
        hit = next((k for k, s in enumerate(spans) if s.start <= centre < s.end), None)
        ok = hit is not None and spans[hit].positive and hit not in used
        if ok:
            used.add(hit)
        rows.append(dict(start=int(starts[i]), centre=int(centre), score=float(scores[i]), correct=bool(ok), span=hit))
    rows.sort(key=lambda r: r["centre"])
    return rows, used


def counts(rows, spans):
    """TP, FP, FN for one recording."""
    tp = sum(r["correct"] for r in rows)
    fp = len(rows) - tp
    fn = sum(s.positive for s in spans) - tp
    return tp, fp, fn


def prf(tp, fp, fn):
    """Precision, recall, F1 (a ratio with a zero denominator is reported as 0)."""
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f
