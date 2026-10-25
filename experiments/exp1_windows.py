"""Experiments 1 and 2: matched-filter output for rectangular / Hamming / Taylor, PSLR table.
Also makes the 'why pulse compression' picture used in the report introduction."""
import numpy as np

from common import (BLUE, GREY, ORANGE, WIN_COLOR, plt, save_fig, update_results, write_table)
from src.metrics import window_metrics
from src.pipeline import RadarConfig, matched_power
from src.simulation import clean_signal, simulate_rx

cfg = RadarConfig()
delay = 0.01
rows, res = [], {}
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for w in ("rectangular", "hamming", "taylor"):
    c = RadarConfig(window=w)
    env, _ = matched_power(clean_signal(c, [delay], [1.0]), c)
    p = int(np.argmax(env))
    rng_m = (np.arange(len(env)) - delay * c.fs) / c.fs * c.c / 2 * 100        # cm
    db = 20 * np.log10(np.maximum(env / env[p], 1e-6))
    m = window_metrics(cfg, w)
    axes[0].plot(rng_m, db, color=WIN_COLOR[w], lw=1.4,
                 label=f"{w}  (PSLR {m['pslr_db']:.1f} dB)")
    axes[1].plot(rng_m, env / env[p], color=WIN_COLOR[w], lw=1.6, label=w)
    rows.append([w, f"{m['pslr_db']:.2f}", f"{m['width3db_m'] * 100:.2f}", f"{m['null_width_m'] * 100:.2f}",
                 f"{m['snr_loss_db']:.2f}"])
    res[w] = m
axes[0].set(xlim=(-40, 40), ylim=(-65, 3), xlabel="range offset from target (cm)",
            ylabel="matched-filter output (dB re peak)", title="Sidelobes: what the filter does away from the target")
axes[0].legend(loc="upper right")
axes[1].set(xlim=(-6, 6), xlabel="range offset from target (cm)", ylabel="amplitude (linear)",
            title="Zoom on the main lobe: windows make it wider")
axes[1].axhline(10 ** (-3 / 20), color="k", lw=0.6, ls=":")
axes[1].text(5.9, 0.72, "-3 dB", ha="right", fontsize=8)
axes[1].legend()
save_fig(fig, "fig1_windows.png")
write_table("windows", ["window", "PSLR_dB", "mainlobe_-3dB_width_cm", "mainlobe_null_to_null_cm",
                        "SNR_loss_dB"], rows)
update_results("windows", res)

# --- pulse compression picture: echoes invisible in raw data, obvious after the filter
rng = np.random.default_rng(3)
c = RadarConfig(window="taylor", record_s=0.04)
rx, _, d0 = simulate_rx(c, [1.2, 3.0], [0.7, 0.5], -6, rng=rng)
env, _ = matched_power(rx, c)
t = np.arange(c.n_samples) / c.fs * 1000
fig, ax = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True)
ax[0].plot(t, rx, color=GREY, lw=0.5)
ax[0].set(ylabel="microphone signal", title="Before: the echoes are buried in noise (per-sample SNR -6 dB)")
ax[1].plot(t, env, color=BLUE, lw=1)
for r, name in ((1.2, "echo 1: 1.2 m"), (3.0, "echo 2: 3.0 m")):
    tt = (d0 + 2 * r / c.c) * 1000
    ax[1].annotate(name, (tt, env[int(round(tt * c.fs / 1000))]), xytext=(tt + 1.5, env.max() * 0.45),
                   arrowprops=dict(arrowstyle="->", color=ORANGE), color=ORANGE)
ax[1].annotate("direct sound", (d0 * 1000, env.max()), xytext=(d0 * 1000 + 3, env.max() * 0.9),
               arrowprops=dict(arrowstyle="->", color=GREY), color=GREY)
ax[1].set(xlabel="time (ms)", ylabel="matched-filter output", title="After: pulse compression turns each echo into a sharp peak")
save_fig(fig, "fig0_pulse_compression.png")
