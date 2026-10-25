"""Normalised cross-correlation template matching (FFT based) and peak picking, in NumPy."""
import numpy as np


def ncc(x, t, min_energy_ratio=1e-3):
    """Normalised cross-correlation of template `t` against every window of signal `x`.

        score[k] = sum_n x[k+n] t[n] / ( sqrt(sum_n x[k+n]^2) * sqrt(sum_n t[n]^2) )

    The numerator is computed with FFTs (zero-padded -> linear correlation); the window energy
    in the denominator comes from a running sum of x^2.  Score is in [-1, 1]; 1.0 means the window is
    an exact (scaled) copy of the template.  Windows whose energy is below `min_energy_ratio`
    x the template energy (silence, tiny noise) get score 0 so quiet gaps cannot score highly.
    Returns an array of length len(x) - len(t) + 1; index k is the window start in samples.
    """
    x = np.asarray(x, float)
    t = np.asarray(t, float)
    n, m = len(x), len(t)
    if m > n:
        return np.zeros(0)
    n_out = n - m + 1
    nfft = 1 << int(np.ceil(np.log2(n + m - 1)))
    num = np.fft.irfft(np.fft.rfft(x, nfft) * np.conj(np.fft.rfft(t, nfft)), nfft)[:n_out]
    csum = np.concatenate(([0.0], np.cumsum(x * x)))
    win_e = csum[m:m + n_out] - csum[:n_out]
    t_e = float(np.sum(t * t))
    ok = win_e > max(min_energy_ratio * t_e, 1e-12)
    out = np.zeros(n_out)
    out[ok] = num[ok] / (np.sqrt(win_e[ok]) * np.sqrt(t_e))
    return np.clip(out, -1.0, 1.0)


def pick_peaks(score, threshold, min_sep):
    """Non-maximum suppression: strongest first, drop any peak within min_sep samples of a kept one.

    Only local maxima >= threshold are candidates. Returns (indices, scores) sorted by position.
    """
    score = np.asarray(score)
    if len(score) < 3:
        return np.array([], int), np.array([])
    left, right = score[:-2], score[2:]
    mid = score[1:-1]
    cand = np.flatnonzero((mid >= left) & (mid > right) & (mid >= threshold)) + 1
    if score[0] >= threshold and score[0] > score[1]:
        cand = np.concatenate(([0], cand))
    kept = []
    for i in cand[np.argsort(-score[cand])]:
        if all(abs(i - j) >= min_sep for j in kept):
            kept.append(i)
    kept = np.array(sorted(kept), int)
    return kept, score[kept]
