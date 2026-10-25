"""Linear-FM (chirp) generation and the basic radar/sonar formulas."""
import numpy as np

C_AIR = 343.0  # speed of sound in air at ~20 C, m/s (a parameter everywhere)


def lfm_chirp(f0, bandwidth, duration, fs, amplitude=1.0):
    """Real linear-FM chirp sweeping f0 -> f0+bandwidth over `duration` seconds.

    s(t) = A cos(2 pi (f0 t + 0.5 k t^2)),  k = B / T  (sweep rate, Hz/s).
    """
    if f0 + bandwidth > fs / 2:
        raise ValueError(
            f"chirp top frequency {f0 + bandwidth:.0f} Hz exceeds Nyquist {fs / 2:.0f} Hz")
    n = int(round(duration * fs))
    t = np.arange(n) / fs
    return amplitude * np.cos(2 * np.pi * (f0 * t + 0.5 * (bandwidth / duration) * t ** 2))


def chirp_at(t, f0, bandwidth, duration, amplitude=1.0):
    """The same chirp evaluated at arbitrary times `t` (zero outside [0, T]).

    Used to build echoes with exact (fractional-sample) delays: echo(t) = chirp_at(t - tau).
    """
    t = np.asarray(t, dtype=float)
    s = amplitude * np.cos(2 * np.pi * (f0 * t + 0.5 * (bandwidth / duration) * t ** 2))
    return np.where((t >= 0) & (t < duration), s, 0.0)


def range_resolution(bandwidth, c=C_AIR):
    """Two-way range resolution  dR = c / (2 B)  (metres)."""
    return c / (2.0 * bandwidth)


def max_unambiguous_range(pri, c=C_AIR):
    """Largest range whose echo arrives before the next chirp:  R = c * PRI / 2.

    With back-to-back chirps PRI equals the chirp length T, so R = c T / 2.
    """
    return c * pri / 2.0


def delay_to_range(delay_s, c=C_AIR):
    """Round-trip delay (s) -> range (m):  R = c * delay / 2."""
    return c * np.asarray(delay_s) / 2.0


def range_to_delay(range_m, c=C_AIR):
    """Range (m) -> round-trip delay (s)."""
    return 2.0 * np.asarray(range_m) / c


def time_bandwidth_product(bandwidth, duration):
    """B*T: how much longer the chirp is than the 1/B pulse it compresses to."""
    return bandwidth * duration
