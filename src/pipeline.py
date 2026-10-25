"""End-to-end processing: matched filter -> power -> CFAR -> peak picking -> ranges."""
from dataclasses import dataclass, field

import numpy as np

from .cfar import cfar_threshold
from .chirp import C_AIR, lfm_chirp, max_unambiguous_range, range_resolution
from .matched_filter import matched_filter
from .windows import get_window


@dataclass(frozen=True)
class RadarConfig:
    """All settings of one run (hashable, so Streamlit can cache on it)."""
    fs: float = 48000.0         # sample rate, Hz
    f0: float = 3000.0          # chirp start frequency, Hz
    bandwidth: float = 8000.0   # chirp bandwidth B, Hz
    duration: float = 0.010     # chirp length T, s
    record_s: float = 0.060     # length of the recorded window, s
    c: float = C_AIR            # speed of sound, m/s
    window: str = "taylor"      # replica window: rectangular / hamming / taylor
    detector: str = "os"        # 'ca' or 'os'
    n_train: int = 16           # training cells per side
    n_guard: int = 4            # guard cells per side
    pfa: float = 1e-4           # design false-alarm probability per cell
    k_frac: float = 0.75        # OS-CFAR rank as a fraction of the training cells
    stride: int = 0             # training-cell spacing; 0 = auto = round(fs / B)

    @property
    def n_samples(self):
        return int(round(self.record_s * self.fs))

    @property
    def cell_stride(self):
        return self.stride if self.stride > 0 else max(1, int(round(self.fs / self.bandwidth)))

    @property
    def resolution_m(self):
        return range_resolution(self.bandwidth, self.c)

    @property
    def unambiguous_m(self):
        return max_unambiguous_range(self.record_s, self.c)

    def reference(self):
        return lfm_chirp(self.f0, self.bandwidth, self.duration, self.fs)

    def threshold(self, power):
        """CFAR threshold for a power array under this config."""
        kw = dict(n_train=self.n_train, n_guard=self.n_guard, pfa=self.pfa, stride=self.cell_stride)
        if self.detector == "os":
            kw["k_frac"] = self.k_frac
        return cfar_threshold(power, self.detector, **kw)


def matched_power(rx, cfg):
    """Matched-filter envelope and power of `rx` (1-D or batch) under cfg."""
    ref = cfg.reference()
    y = matched_filter(rx, ref, get_window(cfg.window, len(ref)))
    env = np.abs(y)
    return env, env ** 2


def local_peaks(env, mask):
    """Boolean array: cells that are local maxima of env and inside `mask`."""
    left = np.concatenate([np.zeros_like(env[..., :1]), env[..., :-1]], axis=-1)
    right = np.concatenate([env[..., 1:], np.zeros_like(env[..., :1])], axis=-1)
    return mask & (env >= left) & (env > right)


def parabolic_peak(env, i):
    """Sub-sample peak position by fitting a parabola through env[i-1], env[i], env[i+1]."""
    if i <= 0 or i >= len(env) - 1:
        return float(i)
    a, b, c = env[i - 1], env[i], env[i + 1]
    den = a - 2 * b + c
    return float(i) if den == 0 else float(i + 0.5 * (a - c) / den)


def noise_power_estimate(power):
    """Robust noise level: for exponential power, median = mean * ln 2."""
    return float(np.median(power) / np.log(2))


@dataclass
class Result:
    env: np.ndarray
    power: np.ndarray
    threshold: np.ndarray
    det_index: np.ndarray            # fractional sample index of each detection (echoes only)
    det_amp: np.ndarray              # envelope value at each detection
    det_range: np.ndarray            # metres, relative to the direct peak (or record start)
    direct_index: float = None
    direct_snr_db: float = None
    direct_ok: bool = True
    warnings: list = field(default_factory=list)


def process(rx, cfg, use_direct=True, min_direct_snr_db=15.0):
    """Run the whole chain on one record and return a Result.

    use_direct : treat the strongest peak as the direct speaker->mic sound (zero-distance
                 reference); echo ranges are then measured relative to it, which cancels the
                 unknown audio latency.  If it is not clearly above the noise, direct_ok=False.
    """
    env, power = matched_power(rx, cfg)
    thr = cfg.threshold(power)
    mask = power > thr
    peaks = np.flatnonzero(local_peaks(env, mask))
    min_sep = max(2, int(round(cfg.fs / cfg.bandwidth)))
    # keep the strongest peak within every min_sep neighbourhood
    keep = []
    for i in sorted(peaks, key=lambda j: -env[j]):
        if all(abs(i - j) >= min_sep for j in keep):
            keep.append(i)
    keep = np.array(sorted(keep), dtype=int)

    res = Result(env, power, thr, np.array([]), np.array([]), np.array([]))
    ref_idx = 0.0
    if use_direct:
        d = int(np.argmax(env))
        res.direct_index = parabolic_peak(env, d)
        res.direct_snr_db = float(10 * np.log10(power[d] / max(noise_power_estimate(power), 1e-300)))
        res.direct_ok = res.direct_snr_db >= min_direct_snr_db
        if not res.direct_ok:
            res.warnings.append(
                f"No clear direct-path peak (only {res.direct_snr_db:.1f} dB above the noise). "
                "Speaker or microphone may not be working, volume is too low, or noise is too high.")
        ref_idx = res.direct_index
        keep = keep[np.abs(keep - d) >= min_sep]
        keep = keep[keep > d]
    idx = np.array([parabolic_peak(env, int(i)) for i in keep])
    res.det_index = idx
    res.det_amp = env[keep] if len(keep) else np.array([])
    res.det_range = (idx - ref_idx) / cfg.fs * cfg.c / 2.0
    return res


def match_to_truth(true_ranges, det_ranges, tol_m):
    """Pair each true range with the nearest unused detection within tol_m.

    Returns list of (true_range, detected_range or None) and the list of unmatched detections.
    """
    det = list(det_ranges)
    rows = []
    for r in true_ranges:
        best, bd = None, tol_m
        for j, d in enumerate(det):
            if abs(d - r) <= bd:
                best, bd = j, abs(d - r)
        rows.append((r, det.pop(best) if best is not None else None))
    return rows, det
