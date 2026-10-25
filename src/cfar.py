"""CFAR (constant false alarm rate) threshold detectors on matched-filter power.

Both detectors slide over the power |y|^2.  For every cell under test (CUT) they look at
`n_train` training cells on each side, skipping `n_guard` guard cells next to the CUT (so the
target's own energy does not leak into the noise estimate), estimate the local noise level, and
set   threshold = scale * noise_estimate.

Noise-only matched-filter power is exponentially distributed, which gives closed-form scales:
  CA-CFAR (Rohling 1983, cell averaging):  scale = N (Pfa^(-1/N) - 1),  N = number of training cells
  OS-CFAR (ordered statistic): noise estimate = k-th smallest training value;
        Pfa = prod_{i=0}^{k-1} (N-i)/(N-i+scale)   -> solved numerically for `scale`.
Near the ends of the record fewer training cells exist; N (and the scale) adapt per cell.
`stride` > 1 spaces the training cells out; useful when neighbouring MF samples are correlated
(oversampled output) so that the cells really are close to independent.
"""
from functools import lru_cache

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def ca_scale(pfa, n_cells):
    """CA-CFAR threshold multiplier for exponential noise (Rohling)."""
    n = np.asarray(n_cells, dtype=float)
    return n * (pfa ** (-1.0 / n) - 1.0)


@lru_cache(maxsize=4096)
def os_scale(pfa, n_cells, k):
    """OS-CFAR threshold multiplier: solve prod (N-i)/(N-i+T) = Pfa for T by bisection."""
    i = np.arange(k)

    def pf(t):
        return float(np.prod((n_cells - i) / (n_cells - i + t)))

    lo, hi = 0.0, 1.0
    while pf(hi) > pfa:
        hi *= 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if pf(mid) > pfa:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _training_cells(power, n_train, n_guard, stride):
    """Gather the training cells of every CUT -> array (..., L, 2*n_train); missing = +inf."""
    width = n_guard + 1 + stride * (n_train - 1)
    offs = n_guard + 1 + stride * np.arange(n_train)
    cols = np.concatenate([width - offs, width + offs])
    pad = [(0, 0)] * (power.ndim - 1) + [(width, width)]
    padded = np.pad(power, pad, constant_values=np.inf)
    return sliding_window_view(padded, 2 * width + 1, axis=-1)[..., cols]


def _chunked(fn, power, **kw):
    """Run fn on blocks of rows so the gathered training-cell array stays small."""
    if power.ndim == 1:
        return fn(power, **kw)
    flat = power.reshape(-1, power.shape[-1])
    step = max(1, int(1e5 // flat.shape[-1]))
    out = np.concatenate([fn(flat[i:i + step], **kw) for i in range(0, len(flat), step)])
    return out.reshape(power.shape)


def ca_cfar(power, n_train=16, n_guard=2, pfa=1e-4, stride=1):
    """CA-CFAR threshold (same shape as `power`)."""
    return _chunked(_ca_core, np.asarray(power, dtype=float),
                    n_train=n_train, n_guard=n_guard, pfa=pfa, stride=stride)


def _ca_core(power, n_train, n_guard, pfa, stride):
    cells = _training_cells(power, n_train, n_guard, stride)
    ok = np.isfinite(cells)
    n = ok.sum(-1)
    mean = np.where(ok, cells, 0.0).sum(-1) / np.maximum(n, 1)
    scale = np.zeros(n.shape)
    for nn in np.unique(n[n >= 2]):
        scale[n == nn] = ca_scale(pfa, int(nn))
    thr = scale * mean
    return np.where(n >= 2, thr, np.inf)


def os_cfar(power, n_train=16, n_guard=2, pfa=1e-4, k_frac=0.75, stride=1):
    """OS-CFAR threshold: k-th ordered training value, k = k_frac * N."""
    return _chunked(_os_core, np.asarray(power, dtype=float),
                    n_train=n_train, n_guard=n_guard, pfa=pfa, k_frac=k_frac, stride=stride)


def _os_core(power, n_train, n_guard, pfa, k_frac, stride):
    cells = np.sort(_training_cells(power, n_train, n_guard, stride), axis=-1)
    n = np.isfinite(cells).sum(-1)
    k = np.clip(np.ceil(k_frac * n).astype(int), 1, None)
    k = np.minimum(k, np.maximum(n, 1))
    est = np.take_along_axis(cells, (k - 1)[..., None], axis=-1)[..., 0]
    scale = np.zeros(n.shape)
    for nn, kk in {(int(a), int(b)) for a, b in zip(n.ravel(), k.ravel())}:
        if nn >= 2:
            scale[(n == nn) & (k == kk)] = os_scale(float(pfa), nn, kk)
    thr = scale * np.where(np.isfinite(est), est, 0.0)
    return np.where(n >= 2, thr, np.inf)


def cfar_threshold(power, kind="os", **kw):
    """Dispatch by name: 'ca' or 'os'."""
    kind = kind.lower()
    if kind == "ca":
        kw.pop("k_frac", None)
        return ca_cfar(power, **kw)
    if kind == "os":
        return os_cfar(power, **kw)
    raise ValueError("kind must be 'ca' or 'os'")
