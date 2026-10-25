"""FFT-based matched filter (pulse compression), written from scratch in NumPy."""
import numpy as np

from .windows import get_window


def _fast_len(n):
    """Next power of two >= n (fast FFT size)."""
    return 1 << int(np.ceil(np.log2(max(n, 2))))


def matched_filter(rx, ref, window=None):
    """Correlate `rx` with the reference chirp; return the *analytic* output.

    Matched filter impulse response is h[n] = conj(ref[-n]) (time-reversed conjugate).
    Convolving with h equals multiplying spectra:  Y = RX * conj(REF).
    Output index k is "the reference starts k samples after the record start".

    window : None / name / array - amplitude weighting of the replica (sidelobe control).
    Returns complex array, same length as rx (last axis); .real is the plain correlation,
    abs() is the envelope used for detection.  rx may be 1-D or (trials, samples).
    """
    rx = np.asarray(rx)
    n = rx.shape[-1]
    ref = np.asarray(ref, dtype=float)
    if isinstance(window, str) or window is None:
        window = get_window(window, len(ref))
    ref_w = ref * window
    nfft = _fast_len(n + len(ref) - 1)          # zero-pad -> linear, not circular, correlation
    spec = np.fft.fft(rx, nfft, axis=-1) * np.conj(np.fft.fft(ref_w, nfft))
    # keep positive frequencies only (x2): the inverse FFT is then the analytic signal
    spec[..., nfft // 2 + 1:] = 0
    spec[..., 1:nfft // 2] *= 2
    return np.fft.ifft(spec, axis=-1)[..., :n]


def matched_filter_direct(rx, ref, window=None):
    """Slow reference version: convolve with the time-reversed reference (for testing)."""
    ref = np.asarray(ref, dtype=float)
    if isinstance(window, str) or window is None:
        window = get_window(window, len(ref))
    h = (ref * window)[::-1]
    return np.convolve(rx, h, mode="full")[len(ref) - 1:len(ref) - 1 + len(rx)]


def window_snr_loss_db(ref, window):
    """Peak-SNR loss (dB) of a windowed replica relative to the unwindowed matched filter.

    Peak = sum(w ref^2); noise power ~ sum(w^2 ref^2)  ->  loss vs the rectangular case.
    """
    w = get_window(window, len(ref)) if isinstance(window, str) or window is None else window
    r2 = np.asarray(ref) ** 2
    snr = np.sum(w * r2) ** 2 / np.sum(w ** 2 * r2)
    return float(10 * np.log10(np.sum(r2) / snr))
