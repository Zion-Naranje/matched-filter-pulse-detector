"""Explanatory figure: how a CFAR looks at one cell under test (CUT) and builds a threshold."""
import numpy as np

from common import BLUE, GREEN, GREY, ORANGE, RED, plt, save_fig
from src.pipeline import RadarConfig, matched_power
from src.simulation import simulate_rx

cfg = RadarConfig(detector="os", record_s=0.03)
rng = np.random.default_rng(8)
rx, _, d0 = simulate_rx(cfg, [1.0, 1.8], [0.9, 1.0], -4, direct_delay_s=None, rng=rng)
env, power = matched_power(rx, cfg)
thr = np.sqrt(cfg.threshold(power))
x = np.arange(cfg.n_samples)
cut = int(round(2 * 1.8 / cfg.c * cfg.fs))
s, g, n = cfg.cell_stride, cfg.n_guard, cfg.n_train
train = np.concatenate([cut - g - 1 - s * np.arange(n), cut + g + 1 + s * np.arange(n)])
guard = np.concatenate([np.arange(cut - g, cut), np.arange(cut + 1, cut + g + 1)])
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.plot(x, env, color=GREY, lw=1.1, label="matched-filter output")
ax.plot(x, thr, color=BLUE, lw=1.6, label="CFAR threshold (follows the local noise level)")
ax.scatter(train, env[train], color=GREEN, s=22, zorder=3, label=f"training cells ({2 * n}) -> estimate the noise")
ax.scatter(guard, env[guard], color=ORANGE, s=18, zorder=3, label=f"guard cells ({2 * g}) -> ignored (target's own lobe)")
ax.scatter([cut], [env[cut]], color=RED, s=60, zorder=4, marker="D", label="cell under test")
ax.set(xlim=(cut - 130, cut + 130), xlabel="sample index", ylabel="amplitude",
       title="CFAR: threshold = scale x noise level measured in the training cells around each cell")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=8)
save_fig(fig, "fig_cfar_geometry.png")
