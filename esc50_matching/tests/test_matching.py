import numpy as np
import pytest

from src.matching import ncc, pick_peaks
from src.metrics import counts, label_detections, prf
from src.recording import Span


def test_self_ncc_is_one_at_zero_lag():
    t = np.random.default_rng(0).standard_normal(800)
    s = ncc(t, t)
    assert len(s) == 1 and s[0] == pytest.approx(1.0, abs=1e-9)


def test_embedded_template_found_at_correct_position():
    rng = np.random.default_rng(1)
    t = rng.standard_normal(500)
    x = 0.05 * rng.standard_normal(6000)
    x[2345:2345 + 500] += 0.7 * t                      # scaled copy inside noise
    s = ncc(x, t)
    assert abs(int(np.argmax(s)) - 2345) <= 1          # within one hop (1 sample)
    starts, vals = pick_peaks(s, 0.5, 500)
    assert len(starts) == 1 and abs(starts[0] - 2345) <= 1


def test_silence_scores_zero_and_scale_invariance():
    rng = np.random.default_rng(2)
    t = rng.standard_normal(300)
    x = np.concatenate([np.zeros(1000), 3.0 * t, np.zeros(1000)])
    s = ncc(x, t)
    assert s[1000] == pytest.approx(1.0, abs=1e-9) and s[:500].max() == 0.0


def test_metrics_toy_case():
    spans = [Span(0, 100, "dog", "a", True), Span(200, 300, "dog", "b", True), Span(400, 500, "rain", "c", False)]
    # detections (start, score) with template length 40 -> centres 20, 70(duplicate in span a), 420 (wrong class), 700 (silence)
    starts = np.array([0, 50, 400, 680])
    scores = np.array([0.9, 0.6, 0.8, 0.5])
    rows, _ = label_detections(starts, scores, 40, spans)
    tp, fp, fn = counts(rows, spans)
    assert (tp, fp, fn) == (1, 3, 1)
    p, r, f = prf(tp, fp, fn)
    assert p == pytest.approx(0.25) and r == pytest.approx(0.5) and f == pytest.approx(1 / 3)
    assert prf(0, 0, 2) == (0.0, 0.0, 0.0)
