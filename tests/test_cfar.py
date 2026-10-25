"""CFAR tests: false-alarm rate, detection of a known target, and the OS-vs-CA masking case."""
import numpy as np
import pytest

from src.cfar import ca_cfar, ca_scale, os_cfar, os_scale
from src.metrics import monte_carlo, noise_only_pfa
from src.pipeline import RadarConfig, process
from src.simulation import simulate_rx


def test_ca_scale_formula():
    n = 32
    assert ca_scale(1e-4, n) == pytest.approx(n * (1e-4 ** (-1 / n) - 1))


def test_os_scale_solves_pfa():
    n, k = 32, 24
    t = os_scale(1e-4, n, k)
    i = np.arange(k)
    assert np.prod((n - i) / (n - i + t)) == pytest.approx(1e-4, rel=1e-6)


@pytest.mark.parametrize("fn", [ca_cfar, os_cfar])
def test_false_alarm_rate_on_exponential_noise(fn):
    """Theory check: iid exponential cells -> measured Pfa matches the design Pfa."""
    pfa = 1e-3
    p = np.random.default_rng(3).exponential(size=(400, 5000))      # 2e6 cells -> ~2000 alarms
    measured = (p > fn(p, n_train=16, n_guard=2, pfa=pfa)).mean()
    assert measured == pytest.approx(pfa, rel=0.15)


@pytest.mark.parametrize("det", ["ca", "os"])
def test_false_alarm_rate_on_matched_filter_noise(det):
    """Real MF output: samples are correlated, so we space training cells by fs/B.
    Measured Pfa must be at or below ~1.5x the design value (it is conservative, see report)."""
    cfg = RadarConfig(detector=det, pfa=1e-3, window="rectangular")
    measured = noise_only_pfa(cfg, trials=300, seed=7)
    assert 0.3e-3 < measured < 1.5e-3


@pytest.mark.parametrize("det", ["ca", "os"])
def test_detects_known_target_and_rejects_pure_noise(det):
    cfg = RadarConfig(detector=det)
    rng = np.random.default_rng(11)
    rx, _, _ = simulate_rx(cfg, [1.5], [0.6], 0, rng=rng)
    res = process(rx, cfg)
    assert len(res.det_range) == 1 and abs(res.det_range[0] - 1.5) < 0.01
    m = monte_carlo(cfg, [1.5], [1.0], -3, trials=100, seed=2)      # strong -> found
    assert m["pd"][0] > 0.95
    noise = np.random.default_rng(5).standard_normal((100, cfg.n_samples))
    from src.pipeline import matched_power
    _, power = matched_power(noise, cfg)
    assert (power > cfg.threshold(power)).sum(1).mean() < 1.0       # <1 false alarm per 2880-cell record


def test_os_cfar_beats_ca_cfar_in_masking_case():
    """Weak target 4.3 cm from a target 9.5 dB stronger (inside the training window):
    CA-CFAR's noise estimate is inflated by the strong one and the weak target is masked."""
    d = 12 * 343 / 2 / 48000
    kw = dict(ranges_m=[1.0, 1.0 + d], strengths=[1.0, 3.0], snr_db=-8, trials=200, seed=1,
              tol_samples=3)
    single_ca = monte_carlo(RadarConfig(detector="ca"), [1.0], [1.0], -8, trials=200, seed=1,
                            tol_samples=3)["pd"][0]
    ca = monte_carlo(RadarConfig(detector="ca"), **kw)["pd"]
    os_ = monte_carlo(RadarConfig(detector="os"), **kw)["pd"]
    assert single_ca > 0.9                  # alone, the weak target is easily detected
    assert ca[0] < 0.2                      # masked by CA-CFAR
    assert os_[0] > 0.8                     # OS-CFAR still finds it
    assert ca[1] > 0.95 and os_[1] > 0.95   # the strong one is found by both


def test_pure_noise_triggers_no_direct_peak_warning():
    cfg = RadarConfig()
    rx = np.random.default_rng(0).standard_normal(cfg.n_samples)
    res = process(rx, cfg)
    assert not res.direct_ok and res.warnings
