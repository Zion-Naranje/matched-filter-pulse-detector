"""Amplitude windows applied to the matched-filter replica to lower sidelobes."""
import numpy as np
from scipy.signal import windows as _sw

WINDOW_NAMES = ("rectangular", "hamming", "taylor")


def get_window(name, n):
    """Return an n-point window. Taylor uses 5 near-in sidelobes at -40 dB."""
    name = (name or "rectangular").lower()
    if name in ("rectangular", "rect", "none"):
        return np.ones(n)
    if name == "hamming":
        return 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(n) / (n - 1))
    if name == "taylor":
        return _sw.taylor(n, nbar=5, sll=40, norm=False)
    raise ValueError(f"unknown window '{name}', choose from {WINDOW_NAMES}")
