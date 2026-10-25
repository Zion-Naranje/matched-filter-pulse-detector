"""Simulated received signals: delayed chirp echoes + white Gaussian noise."""
import numpy as np

from .chirp import chirp_at, range_to_delay


def clean_signal(cfg, delays_s, amps):
    """Sum of delayed copies of the transmitted chirp (exact fractional delays)."""
    t = np.arange(cfg.n_samples) / cfg.fs
    rx = np.zeros(cfg.n_samples)
    for tau, a in zip(delays_s, amps):
        rx += chirp_at(t - tau, cfg.f0, cfg.bandwidth, cfg.duration, a)
    return rx


def noise_sigma(snr_db):
    """Noise std so that a unit-amplitude chirp (power 1/2) has the given per-sample SNR."""
    return np.sqrt(0.5 / 10 ** (snr_db / 10.0))


def simulate_rx(cfg, ranges_m, strengths, snr_db, direct_delay_s=0.004,
                direct_strength=1.0, trials=None, rng=None):
    """Received record for targets at `ranges_m` with relative amplitudes `strengths`.

    snr_db is the per-sample SNR of a unit-amplitude chirp; a target of strength a has
    SNR snr_db + 20 log10(a).  If direct_delay_s is not None, a direct speaker->mic arrival
    (strength `direct_strength`) is added, as in live mode.  Echo delays are measured from it.
    Returns (rx, clean, direct_delay_s); rx is (trials, n) when trials is given.
    """
    rng = rng or np.random.default_rng()
    d0 = direct_delay_s or 0.0
    delays = list(d0 + range_to_delay(np.asarray(ranges_m, float), cfg.c))
    amps = list(strengths)
    if direct_delay_s is not None:
        delays.append(direct_delay_s)
        amps.append(direct_strength)
    clean = clean_signal(cfg, delays, amps)
    shape = (cfg.n_samples,) if trials is None else (trials, cfg.n_samples)
    return clean + noise_sigma(snr_db) * rng.standard_normal(shape), clean, direct_delay_s
