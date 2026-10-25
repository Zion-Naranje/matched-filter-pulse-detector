"""Experiments 3 and 4: detection probability and range error vs SNR for CA- and OS-CFAR."""
import numpy as np

from common import DET_COLOR, DET_NAME, plt, save_fig, update_results, write_table
from src.metrics import detection_curve, noise_only_pfa
from src.pipeline import RadarConfig

TRIALS = 1000
SNR = np.arange(-24, -5, 2.0)
R_TRUE = 1.5
out, rows = {}, []
for det in ("ca", "os"):
    cfg = RadarConfig(detector=det)                      # Taylor window, Pfa 1e-4, 16+4 cells/side
    out[det] = detection_curve(cfg, SNR, range_m=R_TRUE, trials=TRIALS, seed=100)
    out[det]["pfa_measured"] = noise_only_pfa(cfg, trials=1000, seed=5)
for i, s in enumerate(SNR):
    ca, os_ = out["ca"], out["os"]
    rows.append([f"{s:.0f}", f"{ca['pd'][i]:.3f}", f"{os_['pd'][i]:.3f}",
                 f"{ca['err_mean_m'][i] * 1000:.2f}", f"{ca['err_std_m'][i] * 1000:.2f}",
                 f"{os_['err_mean_m'][i] * 1000:.2f}", f"{os_['err_std_m'][i] * 1000:.2f}",
                 f"{ca['fa_per_trial'][i]:.3f}", f"{os_['fa_per_trial'][i]:.3f}"])
write_table("pd_range_error_vs_snr",
            ["SNR_dB", "Pd_CA", "Pd_OS", "err_mean_CA_mm", "err_std_CA_mm", "err_mean_OS_mm",
             "err_std_OS_mm", "false_det_per_record_CA", "false_det_per_record_OS"], rows)

fig, ax = plt.subplots(figsize=(7, 4.2))
for det in ("ca", "os"):
    p = out[det]["pd"]
    ci = 1.96 * np.sqrt(p * (1 - p) / TRIALS)            # 95 % binomial interval
    ax.plot(SNR, p, "o-", color=DET_COLOR[det], label=DET_NAME[det], ms=4)
    ax.fill_between(SNR, np.clip(p - ci, 0, 1), np.clip(p + ci, 0, 1), color=DET_COLOR[det], alpha=0.15)
ax.axhline(0.9, color="k", lw=0.6, ls=":")
ax.set(xlabel="input SNR per sample (dB)", ylabel="probability of detection",
       title=f"Detection probability vs SNR (single target at {R_TRUE} m, {TRIALS} trials/point)")
ax.legend(loc="upper left")
save_fig(fig, "fig3_pd_vs_snr.png")

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for det in ("ca", "os"):
    ok = ~np.isnan(out[det]["err_std_m"])
    ax[0].plot(SNR[ok], out[det]["err_std_m"][ok] * 1000, "o-", color=DET_COLOR[det], ms=4, label=DET_NAME[det])
    ax[1].plot(SNR[ok], out[det]["err_mean_m"][ok] * 1000, "o-", color=DET_COLOR[det], ms=4, label=DET_NAME[det])
from src.chirp import range_resolution
res_mm = range_resolution(8000) * 1000
ax[0].axhline(res_mm, color="k", ls=":", lw=0.8)
ax[0].text(SNR[0], res_mm * 0.9, f"one range cell = {res_mm:.1f} mm", fontsize=8, va="top")
ax[0].set(xlabel="input SNR (dB)", ylabel="range error std (mm)", yscale="log",
          title="Spread of the range estimate (only runs that detected)")
ax[1].axhline(0, color="k", lw=0.6)
ax[1].set(xlabel="input SNR (dB)", ylabel="mean range error (mm)", title="Bias of the range estimate")
ax[0].legend()
save_fig(fig, "fig4_range_error.png")
update_results("detection", dict(trials=TRIALS, snr_db=SNR.tolist(), range_m=R_TRUE,
                                 pd_ca=out["ca"]["pd"].tolist(), pd_os=out["os"]["pd"].tolist(),
                                 pfa_design=RadarConfig().pfa, pfa_measured_ca=out["ca"]["pfa_measured"],
                                 pfa_measured_os=out["os"]["pfa_measured"],
                                 err_std_mm_ca=(out["ca"]["err_std_m"] * 1000).tolist(),
                                 err_std_mm_os=(out["os"]["err_std_m"] * 1000).tolist(),
                                 err_mean_mm_ca=(out["ca"]["err_mean_m"] * 1000).tolist(),
                                 err_mean_mm_os=(out["os"]["err_mean_m"] * 1000).tolist()))
print("measured Pfa (noise only): CA", out["ca"]["pfa_measured"], " OS", out["os"]["pfa_measured"],
      " design", RadarConfig().pfa)
