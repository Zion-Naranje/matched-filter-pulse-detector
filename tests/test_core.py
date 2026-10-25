"""Core DSP tests: chirp, matched filter, formulas, windows."""
import numpy as np
import pytest

from src.chirp import (C_AIR, chirp_at, delay_to_range, lfm_chirp, max_unambiguous_range,
                       range_resolution, range_to_delay)
from src.matched_filter import matched_filter, matched_filter_direct, window_snr_loss_db
from src.metrics import window_metrics
from src.pipeline import RadarConfig, matched_power, process
from src.simulation import clean_signal, simulate_rx

CFG = RadarConfig()


def test_chirp_sweeps_f0_to_f1():
    ref = lfm_chirp(3000, 8000, 0.01, 48000)
    assert len(ref) == 480
    f = np.fft.rfftfreq(4800, 1 / 48000)
    first = f[np.argmax(np.abs(np.fft.rfft(ref[:48], 4800)))]     # first 1 ms: ~3000 + 0.5 ms * 800 kHz/s
    last = f[np.argmax(np.abs(np.fft.rfft(ref[-48:], 4800)))]
    assert first == pytest.approx(3400, abs=300) and last == pytest.approx(10600, abs=300)


def test_nyquist_violation_rejected():
    with pytest.raises(ValueError):
        lfm_chirp(20000, 8000, 0.01, 48000)


def test_self_correlation_peaks_at_zero_lag_with_energy_height():
    ref = CFG.reference()
    rx = np.concatenate([ref, np.zeros(500)])
    y = matched_filter(rx, ref, None)
    assert np.argmax(np.abs(y)) == 0
    assert np.abs(y[0]) == pytest.approx(np.sum(ref ** 2), rel=1e-9)   # expected height = energy
    assert y[0].real == pytest.approx(np.sum(ref ** 2), rel=1e-9)


def test_fft_matched_filter_equals_time_reversed_convolution():
    rng = np.random.default_rng(0)
    ref = CFG.reference()
    rx = rng.standard_normal(1500)
    for w in (None, "hamming", "taylor"):
        assert np.allclose(matched_filter(rx, ref, w).real, matched_filter_direct(rx, ref, w), atol=1e-8)


@pytest.mark.parametrize("delay_s", [0.0031, 0.0100007, 0.02317, 0.0409])
def test_delayed_echo_found_within_one_sample(delay_s):
    rx = clean_signal(CFG, [delay_s], [1.0])
    env, _ = matched_power(rx, CFG)
    assert abs(np.argmax(env) - delay_s * CFG.fs) <= 1.0


def test_subsample_range_accuracy_noise_free():
    r_true = 2.0
    rx, _, d0 = simulate_rx(CFG, [r_true], [0.5], 80, direct_delay_s=0.004, rng=np.random.default_rng(1))
    res = process(rx, CFG)
    assert len(res.det_range) == 1
    assert abs(res.det_range[0] - r_true) < 0.003


def test_range_formulas():
    assert range_resolution(8000) == pytest.approx(343 / 16000)
    assert range_resolution(10000, c=340) == pytest.approx(340 / 20000)
    assert max_unambiguous_range(0.01) == pytest.approx(343 * 0.01 / 2)   # PRI = T
    assert delay_to_range(range_to_delay(3.3)) == pytest.approx(3.3)
    assert delay_to_range(0.01, c=343) == pytest.approx(1.715)
    assert CFG.resolution_m == pytest.approx(C_AIR / (2 * CFG.bandwidth))
    assert CFG.unambiguous_m == pytest.approx(C_AIR * CFG.record_s / 2)


def test_rect_mainlobe_width_matches_one_over_bandwidth():
    m = window_metrics(CFG, "rectangular")
    assert m["width3db_m"] == pytest.approx(0.886 * CFG.resolution_m, rel=0.25)   # sinc: 0.886/B
    assert m["pslr_db"] == pytest.approx(-13.3, abs=1.5)                         # sinc sidelobe


def test_windows_reduce_pslr_vs_rectangular():
    rect = window_metrics(CFG, "rectangular")["pslr_db"]
    for w in ("hamming", "taylor"):
        m = window_metrics(CFG, w)
        assert m["pslr_db"] < rect - 15            # >15 dB better sidelobes
        assert m["width3db_m"] > window_metrics(CFG, "rectangular")["width3db_m"]   # price: wider lobe
        assert m["snr_loss_db"] > 0.5              # and some SNR loss


def test_window_snr_loss_zero_for_rectangular():
    assert window_snr_loss_db(CFG.reference(), "rectangular") == pytest.approx(0, abs=1e-9)
