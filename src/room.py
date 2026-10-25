"""Optional stage: length and breadth of a rectangular room from one device's echoes.

Simulation uses the image-source method (Allen & Berkley, 1979).  Estimation uses the fact that
with the laptop in the open, the first-order echoes come from the four walls at path 2*d, and a
wall pair on the same axis also produces a second-order (wall-to-wall) echo at path 2*(d1+d2).
That second echo is how unlabeled echoes are paired into the two axes.
"""
from itertools import combinations_with_replacement

import numpy as np

from .pipeline import process
from .simulation import noise_sigma


def image_sources(room, src, mic, beta, max_order=3, max_path=40.0):
    """Arrival paths and amplitudes at `mic` from source `src` in a box room (Allen-Berkley).

    room = (Lx, Ly, Lz); beta = reflection coefficients (x0, xL, y0, yL, z0, zL).
    Returns (path_m, amp) with amp normalised so the direct sound has amplitude 1 (1/r spreading).
    """
    room, src, mic = (np.asarray(v, float) for v in (room, src, mic))
    b = np.asarray(beta, float).reshape(3, 2)
    n = np.arange(-max_order, max_order + 1)
    q = np.array([0, 1])
    nn, qq = np.meshgrid(n, q, indexing="ij")           # per-axis (n, q) combinations
    nn, qq = nn.ravel(), qq.ravel()
    axes = []
    for k in range(3):
        pos = (1 - 2 * qq) * src[k] + 2 * nn * room[k]   # image coordinate on this axis
        order = np.abs(nn - qq) + np.abs(nn)
        refl = b[k, 0] ** np.abs(nn - qq) * b[k, 1] ** np.abs(nn)
        axes.append((pos - mic[k], order, refl))
    dx, ox, rx_ = axes[0]
    dy, oy, ry = axes[1]
    dz, oz, rz = axes[2]
    d2 = dx[:, None, None] ** 2 + dy[None, :, None] ** 2 + dz[None, None, :] ** 2
    order = ox[:, None, None] + oy[None, :, None] + oz[None, None, :]
    refl = rx_[:, None, None] * ry[None, :, None] * rz[None, None, :]
    dist = np.sqrt(d2).ravel()
    keep = (order.ravel() <= max_order) & (dist < max_path)
    dist, refl = dist[keep], refl.ravel()[keep]
    direct = np.linalg.norm(src - mic)
    return dist, refl * direct / dist


def room_scene(room, center, sep, beta, max_order=3):
    """Laptop at `center`; speaker and mic `sep` m apart along y, symmetric about the centre."""
    c = np.asarray(center, float)
    off = np.array([0.0, sep / 2.0, 0.0])
    return image_sources(room, c + off, c - off, beta, max_order)


def wall_distances(det_range_m, sep):
    """Range relative to the direct peak -> distance from the laptop centre.

    Path = (extra path measured after the direct peak) + sep; wall distance = path / 2.
    """
    return np.asarray(det_range_m) + sep / 2.0


def room_config(**kw):
    """Detector settings used for room echoes: long record, median-like OS-CFAR (k = N/2).

    Dense wall echoes crowd the training cells, so a lower rank k keeps weaker walls detectable.
    """
    from .pipeline import RadarConfig
    base = dict(record_s=0.12, k_frac=0.5, stride=3, n_guard=4, n_train=16, pfa=1e-4)
    base.update(kw)
    return RadarConfig(**base)


def predicted_ranges(left, right, front, back, sep, max_order=3, return_order=False):
    """Echo ranges (path/2) that the image-source model predicts for a room with these wall
    distances (2-D: floor and ceiling ignored); speaker and mic are `sep` apart on the y axis."""
    n = np.arange(-max_order, max_order + 1)
    nn, qq = np.meshgrid(n, [0, 1], indexing="ij")
    nn, qq = nn.ravel(), qq.ravel()
    order = np.abs(nn - qq) + np.abs(nn)
    lx, ly = left + right, front + back
    dx = -2 * qq * left + 2 * nn * lx                       # image offset from the mic, x
    ys_src, ys_mic = front + sep / 2.0, front - sep / 2.0   # y of speaker / microphone
    dy = (1 - 2 * qq) * ys_src + 2 * nn * ly - ys_mic
    tot = order[:, None] + order[None, :]
    dist = np.hypot(dx[:, None], dy[None, :]) / 2.0
    sel = (tot <= max_order) & (dist > 0.3)
    return (dist[sel], tot[sel]) if return_order else dist[sel]


def estimate_room(dists, amps, sep=0.2, tol=0.03, r_min=0.5, max_peaks=24):
    """Assign echo distances to the four walls; return length / breadth.

    Assumes the laptop is placed so the speaker-microphone line is parallel to a wall pair
    ("front/back"); the other pair is "left/right".  Echoes are not labelled, so we test
    hypotheses: pick two echoes as left/right walls and two as front/back walls, require that
    their wall-to-wall echoes (a+b, and (c+d) +- sep/2) exist, then predict *all* image-source
    echoes (Allen & Berkley, up to 3rd order) and count how many detected echoes are explained.
    The hypothesis that explains the most echoes wins.  length = larger total, breadth = smaller.
    """
    d = np.asarray(dists, float)
    a = np.asarray(amps, float)
    ok = d >= r_min
    d, a = d[ok], a[ok] * d[ok]                      # compensate 1/r spreading loss
    d_all = d.copy()                                 # every detected echo, for the miss penalty
    top = np.argsort(-a)[:max_peaks]
    d, a = d[top], a[top] / (a[top].max() if len(top) else 1.0)
    n = len(d)
    if n < 2:
        return dict(ok=False, reason="fewer than two wall echoes found")

    def seen(r):
        j = np.flatnonzero(np.abs(d - r) <= tol)
        return a[j].max() if len(j) else 0.0

    def seen_split(r):
        return max(seen(r), 0.5 * (seen(r - sep / 2) + seen(r + sep / 2)))

    pairs = list(combinations_with_replacement(range(n), 2))
    xs = [(p, q) for p, q in pairs if seen(d[p] + d[q]) > 0]
    ys = [(p, q) for p, q in pairs if seen_split(d[p] + d[q]) > 0]
    best, best_key = None, None
    for p, q in xs:
        for u, v in ys:
            if {p, q} & {u, v}:
                continue
            pred, order = predicted_ranges(d[p], d[q], d[u], d[v], sep, return_order=True)
            hit = np.abs(d[:, None] - pred[None, :]).min(1) <= tol
            near = pred[order <= 2]                  # strong predicted echoes that must exist
            miss = int((np.abs(near[:, None] - d_all[None, :]).min(1) > tol).sum()) if len(d_all) else 0
            key = (int(hit.sum()) - miss, float(a[hit].sum()))
            if best is None or key > best_key:
                best, best_key = ((p, q), (u, v)), key
    if best is None:
        return dict(ok=False, reason="no wall pair confirmed by its wall-to-wall echo")
    (p, q), (u, v) = best
    lr = tuple(sorted((float(d[p]), float(d[q]))))
    fb = tuple(sorted((float(d[u]), float(d[v]))))
    t_lr, t_fb = sum(lr), sum(fb)
    return dict(ok=True, length=max(t_lr, t_fb), breadth=min(t_lr, t_fb),
                left_right=lr, front_back=fb, length_is_front_back=bool(t_fb >= t_lr),
                echoes_explained=best_key[0], echoes_total=n,
                confident=bool(best_key[0] >= 0.6 * n), peaks_m=d, peak_amps=a)


def simulate_room_record(cfg, room, center, sep, beta, snr_db, rng, latency_s=0.004, max_order=3):
    """Noisy recording of one chirp played in a simulated room (direct path at `latency_s`)."""
    from .simulation import clean_signal
    path, amp = room_scene(room, center, sep, beta, max_order)
    delays = latency_s + (path - sep) / cfg.c        # direct arrives exactly at latency_s
    clean = clean_signal(cfg, delays, amp)
    return clean + noise_sigma(snr_db) * rng.standard_normal(cfg.n_samples)


def measure_room(rx, cfg, sep, tol=0.05):
    """Full chain on a recording: matched filter + CFAR + pairing -> estimate dict (+ detections)."""
    res = process(rx, cfg, use_direct=True)
    out = dict(detections=res, ok=False)
    if not res.direct_ok or len(res.det_range) < 2:
        out["reason"] = res.warnings[0] if res.warnings else "too few echoes detected"
        return out
    d = wall_distances(res.det_range, sep)
    est = estimate_room(d, res.det_amp, sep=sep, tol=tol)
    est["detections"] = res
    return est
