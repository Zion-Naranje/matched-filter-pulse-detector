"""Why the default guard is 8 cells: Pd and measured Pfa vs guard cells (design Pfa 1e-4, SNR -10 dB)."""
from dataclasses import replace

from common import update_results, write_table
from src.metrics import monte_carlo, noise_only_pfa
from src.pipeline import RadarConfig

rows, res = [], []
for g in (2, 4, 8, 12):
    line, rec = [g], dict(guard=g)
    for det in ("ca", "os"):
        c = replace(RadarConfig(), detector=det, n_guard=g)
        pd = monte_carlo(c, [1.5], [1.0], -10.0, trials=500, seed=21)["pd"][0]
        pfa = noise_only_pfa(c, trials=500, seed=3)
        line += [f"{pd:.3f}", f"{pfa:.2e}"]
        rec[det] = dict(pd=pd, pfa=pfa)
    rows.append(line)
    res.append(rec)
    print(line)
write_table("guard_sweep", ["guard_cells_per_side", "Pd_CA", "Pfa_CA", "Pd_OS", "Pfa_OS"], rows)
update_results("guard_sweep", res)
