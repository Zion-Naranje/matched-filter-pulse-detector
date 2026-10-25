"""Quality metrics: PSLR / mainlobe width, and Monte Carlo detection statistics."""
import numpy as np

from .chirp import range_to_delay
from .matched_filter import window_snr_loss_db
from .pipeline import local_peaks, matched_power
from .simulation import clean_signal, simulate_rx
from .windows import get_window


def window_metrics(cfg, window, delay_s=0.01):
    """Noise-free single-target matched-filter response -> PSLR and mainlobe widths.

    PSLR  = highest sidelobe relative to the peak (dB, negative).  The mainlobe ends at the
    first null (local minimum) on each side.  Width is the -3 dB width, in metres of range.
    """
    cfg = cfg.__class__(**{**cfg.__dict__, "window": window})
    env, _ = matched_power(clean_signal(cfg, [delay_s], [1.0]), cfg)
    p = int(np.argmax(env))
    db = 20 * np.log10(np.maximum(env / env[p], 1e-12))
    lo = p
    while lo > 0 and env[lo - 1] < env[lo]:
        lo -= 1
    hi = p
    while hi < len(env) - 1 and env[hi + 1] < env[hi]:
        hi += 1
    side = np.concatenate([db[:lo], db[hi + 1:]])
    pslr = float(side.max()) if len(side) else float("-inf")

    def cross(step):
        i = p
        while 0 < i < len(db) - 1 and db[i + step] > -3.0:
            i += step
        j = i + step                       # linear interpolation of the -3 dB crossing
        return i + step * (db[i] + 3.0) / (db[i] - db[j])
    width_samples = cross(+1) - cross(-1)
    return dict(window=window, pslr_db=pslr, width3db_samples=float(width_samples),
                width3db_m=float(width_samples / cfg.fs * cfg.c / 2),
                null_width_m=float((hi - lo) / cfg.fs * cfg.c / 2),
                snr_loss_db=window_snr_loss_db(cfg.reference(), window))


def monte_carlo(cfg, ranges_m, strengths, snr_db, trials=200, seed=0, tol_samples=None):
    """Detection statistics for a known target set (no direct path), many noise draws.

    Returns dict with per-target arrays: pd, err_mean_m, err_std_m, plus fa_per_trial
    (detections farther than tol from every true target).  Range error uses sub-sample peaks.
    """
    rng = np.random.default_rng(seed)
    tol = tol_samples or int(np.ceil(cfg.fs / cfg.bandwidth))
    rx, _, _ = simulate_rx(cfg, ranges_m, strengths, snr_db, direct_delay_s=None,
                           trials=trials, rng=rng)
    env, power = matched_power(rx, cfg)
    pk = local_peaks(env, power > cfg.threshold(power))
    true_idx = range_to_delay(np.asarray(ranges_m, float), cfg.c) * cfg.fs
    pd, em, es = [], [], []
    near = np.zeros(env.shape[-1], bool)
    for ti in true_idx:
        lo, hi = max(int(round(ti)) - tol, 1), min(int(round(ti)) + tol + 1, env.shape[-1] - 1)
        near[lo:hi] = True
        val = np.where(pk[:, lo:hi], env[:, lo:hi], -1.0)
        best = val.argmax(1)
        found = val.max(1) > 0
        idx = lo + best
        r = np.arange(len(env))
        a, b, c_ = env[r, idx - 1], env[r, idx], env[r, np.minimum(idx + 1, env.shape[-1] - 1)]
        den = a - 2 * b + c_
        frac = idx + np.where(den == 0, 0.0, 0.5 * (a - c_) / np.where(den == 0, 1, den))
        err = (frac[found] - ti) / cfg.fs * cfg.c / 2.0
        pd.append(found.mean())
        em.append(err.mean() if len(err) else np.nan)
        es.append(err.std() if len(err) else np.nan)
    fa = (pk & ~near).sum(1).mean()
    return dict(pd=np.array(pd), err_mean_m=np.array(em), err_std_m=np.array(es),
                fa_per_trial=float(fa), trials=trials)


def noise_only_pfa(cfg, trials=200, seed=0):
    """Measured false-alarm probability per cell on noise-only data (vs the design cfg.pfa)."""
    rng = np.random.default_rng(seed)
    rx = rng.standard_normal((trials, cfg.n_samples))
    _, power = matched_power(rx, cfg)
    return float((power > cfg.threshold(power)).mean())


def detection_curve(cfg, snr_list, range_m=1.0, strength=1.0, trials=100, seed=0):
    """Pd, range error and false alarms vs SNR for one target."""
    out = [monte_carlo(cfg, [range_m], [strength], s, trials, seed + i)
           for i, s in enumerate(snr_list)]
    return dict(snr_db=np.asarray(snr_list, float),
                pd=np.array([o["pd"][0] for o in out]),
                err_mean_m=np.array([o["err_mean_m"][0] for o in out]),
                err_std_m=np.array([o["err_std_m"][0] for o in out]),
                fa_per_trial=np.array([o["fa_per_trial"] for o in out]))
