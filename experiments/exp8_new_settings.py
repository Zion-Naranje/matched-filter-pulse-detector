"""'Tests on new settings': re-run the key checks with settings different from the defaults."""
from dataclasses import replace

import numpy as np

from common import update_results, write_table
from src.metrics import monte_carlo, noise_only_pfa, window_metrics
from src.pipeline import RadarConfig

TRIALS, SNR = 500, -10.0
base = RadarConfig()
settings = [
    ("default (B 8 kHz, T 10 ms, Taylor, Pfa 1e-4, 16 train, 8 guard cells)", base),
    ("narrow band B 3 kHz, T 20 ms", replace(base, bandwidth=3000.0, duration=0.020)),
    ("wide band B 16 kHz, T 5 ms, f0 2 kHz", replace(base, f0=2000.0, bandwidth=16000.0, duration=0.005)),
    ("rectangular window", replace(base, window="rectangular")),
    ("Hamming window", replace(base, window="hamming")),
    ("Pfa 1e-2", replace(base, pfa=1e-2)),
    ("fewer training cells (8 per side)", replace(base, n_train=8)),
    ("warm air c = 346 m/s", replace(base, c=346.0)),
]
rows, res = [], []
for name, cfg in settings:
    r_true = 1.5
    line = [name, f"{cfg.resolution_m * 100:.2f}", f"{window_metrics(cfg, cfg.window)['pslr_db']:.1f}"]
    rec = dict(name=name)
    for det in ("ca", "os"):
        c = replace(cfg, detector=det)
        m = monte_carlo(c, [r_true], [1.0], SNR, trials=TRIALS, seed=21)
        pfa = noise_only_pfa(c, trials=400, seed=9)
        err = m["err_std_m"][0] * 1000
        line += [f"{m['pd'][0]:.3f}", f"{pfa:.2e}", f"{err:.2f}"]
        rec[det] = dict(pd=m["pd"][0], pfa=pfa, err_std_mm=err)
    rows.append(line)
    res.append(rec)
    print(line)
write_table("new_settings", ["setting", "range_resolution_cm", "PSLR_dB", "Pd_CA", "Pfa_CA", "err_std_CA_mm",
                             "Pd_OS", "Pfa_OS", "err_std_OS_mm"], rows)
update_results("new_settings", dict(snr_db=SNR, trials=TRIALS, rows=res))
