"""Experiment 5: two close targets - the strong one masks the weak one for CA-CFAR."""
import numpy as np

from common import BLUE, DET_COLOR, DET_NAME, GREY, ORANGE, plt, save_fig, update_results, write_table
from src.metrics import monte_carlo
from src.pipeline import RadarConfig, matched_power
from src.simulation import simulate_rx

SEP_SAMPLES, SNR, STR_A, STR_B, TRIALS = 12, -8.0, 1.0, 3.0, 1000
R_A = 1.0
R_B = R_A + SEP_SAMPLES * 343 / 2 / 48000
base = RadarConfig()
print(f"target A {R_A:.3f} m (strength {STR_A}), B {R_B:.3f} m (strength {STR_B}); "
      f"separation {100 * (R_B - R_A):.1f} cm = {(R_B - R_A) / base.resolution_m:.1f} range cells; SNR {SNR} dB")

stats = {}
for det in ("ca", "os"):
    cfg = RadarConfig(detector=det)
    alone = monte_carlo(cfg, [R_A], [STR_A], SNR, TRIALS, seed=1, tol_samples=3)["pd"][0]
    both = monte_carlo(cfg, [R_A, R_B], [STR_A, STR_B], SNR, TRIALS, seed=1, tol_samples=3)["pd"]
    stats[det] = dict(pd_A_alone=alone, pd_A=both[0], pd_B=both[1])
write_table("masking", ["detector", "Pd_weak_target_alone", "Pd_weak_target_with_strong_neighbour",
                        "Pd_strong_target"],
            [[DET_NAME[d], f"{s['pd_A_alone']:.3f}", f"{s['pd_A']:.3f}", f"{s['pd_B']:.3f}"] for d, s in stats.items()])
update_results("masking", dict(sep_cm=100 * (R_B - R_A), snr_db=SNR, strengths=[STR_A, STR_B], trials=TRIALS, **stats))

# one example record
rng = np.random.default_rng(1)
rx, _, d0 = simulate_rx(base, [R_A, R_B], [STR_A, STR_B], SNR, direct_delay_s=None, rng=rng)
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw=dict(width_ratios=[1.6, 1]))
x = np.arange(base.n_samples) / base.fs * 343 / 2 * 100
for det in ("ca", "os"):
    cfg = RadarConfig(detector=det)
    env, power = matched_power(rx, cfg)
    thr = np.sqrt(cfg.threshold(power))
    if det == "ca":
        ax[0].plot(x, env, color=GREY, lw=1.2, label="matched-filter output")
    ax[0].plot(x, thr, color=DET_COLOR[det], lw=1.6, ls="-" if det == "os" else "--", label=f"{DET_NAME[det]} threshold")
for r, nm in ((R_A, "A (weak)"), (R_B, "B (strong)")):
    ax[0].axvline(r * 100, color="k", lw=0.5, ls=":")
    ax[0].text(r * 100, ax[0].get_ylim()[1] if False else 0, nm, rotation=90, va="bottom", ha="right", fontsize=8)
ax[0].set(xlim=(R_A * 100 - 25, R_B * 100 + 25), xlabel="range (cm)", ylabel="amplitude",
          title="Same data, two thresholds: CA-CFAR's is pushed above weak target A")
ax[0].legend(loc="upper left")
w = 0.35
for i, det in enumerate(("ca", "os")):
    s = stats[det]
    ax[1].bar(np.arange(2) + (i - 0.5) * w, [s["pd_A"], s["pd_B"]], w, color=DET_COLOR[det], label=DET_NAME[det])
    for j, v in enumerate([s["pd_A"], s["pd_B"]]):
        ax[1].text(j + (i - 0.5) * w, v + 0.02, f"{v:.2f}", ha="center", fontsize=8)
ax[1].set(xticks=[0, 1], xticklabels=["A: weak target", "B: strong target"], ylim=(0, 1.3),
          ylabel="probability of detection", title=f"{TRIALS} trials")
ax[1].legend(loc="upper center", ncol=2)
save_fig(fig, "fig5_masking.png")
print(stats)
