"""Build test recordings by joining clips with 1 s of silence; keep the exact span of each clip."""
from dataclasses import dataclass

import numpy as np

from .dataset import CLASSES, SR


@dataclass
class Span:
    start: int          # first sample
    end: int            # one past the last sample
    category: str
    filename: str
    positive: bool      # True if this clip is an occurrence of the template sound


@dataclass
class Recording:
    signal: np.ndarray
    spans: list
    sr: int = SR


def join_clips(clips, gap_s=1.0, sr=SR):
    """clips: list of (audio, category, filename, positive).  Returns Recording (silence between clips)."""
    gap = np.zeros(int(gap_s * sr))
    parts, spans, pos = [], [], 0
    for i, (a, cat, fn, is_pos) in enumerate(clips):
        if i:
            parts.append(gap)
            pos += len(gap)
        parts.append(a)
        spans.append(Span(pos, pos + len(a), cat, fn, is_pos))
        pos += len(a)
    return Recording(np.concatenate(parts), spans, sr)


def build_recording(ds, template_cat, template_file, seed, n_pos=2, n_neg=3, mode="class",
                    classes=CLASSES, gap_s=1.0, repeat_snr_db=20.0):
    """Random mix with n_pos occurrences of the template sound and n_neg clips of other classes.

    mode "class"  : positives are *other* clips of the template's class (folds 2-5, never the template).
    mode "repeat" : positives are the template clip itself, gain 0.5-1.5 and white noise at repeat_snr_db.
    Negatives come from the other classes (folds 2-5).  Order is random (set by seed).
    """
    rng = np.random.default_rng(seed)
    clips = []
    if mode == "repeat":
        base = ds.load(template_file)
        for _ in range(n_pos):
            a = rng.uniform(0.5, 1.5) * base
            a = a + rng.standard_normal(len(a)) * np.sqrt(np.mean(a ** 2) / 10 ** (repeat_snr_db / 10))
            clips.append((a, template_cat, template_file, True))
    else:
        pool = [f for f in ds.clips_of(template_cat, folds={2, 3, 4, 5}) if f != template_file]
        for f in rng.choice(pool, n_pos, replace=False):
            clips.append((ds.load(f), template_cat, f, True))
    others = [c for c in classes if c != template_cat]
    for _ in range(n_neg):
        c = others[rng.integers(len(others))]
        f = rng.choice(ds.clips_of(c, folds={2, 3, 4, 5}))
        clips.append((ds.load(f), c, f, False))
    order = rng.permutation(len(clips))
    return join_clips([clips[i] for i in order], gap_s)
