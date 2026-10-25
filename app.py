"""Matched-filter chirp ranging with CFAR detection - interactive Streamlit app.

Run:  streamlit run app.py
Simulation mode (default) and live one-device mode share exactly the same DSP code in src/.
"""
from dataclasses import replace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from src.audio_io import AudioUnavailable, audio_status, live_config, record_with_playback
from src.chirp import C_AIR, range_to_delay
from src.metrics import detection_curve, window_metrics
from src.pipeline import RadarConfig, match_to_truth, matched_power, process
from src.plots import BLUE, GREEN, GREY, ORANGE, RED, draw_room
from src.room import measure_room, room_config, simulate_room_record
from src.simulation import simulate_rx
from src.windows import WINDOW_NAMES

plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": 0.25, "font.size": 9, "legend.frameon": False})
st.set_page_config(page_title="Chirp ranging with CFAR", layout="wide")

# ----------------------------------------------------------------- cached heavy work
@st.cache_data(show_spinner=False)
def run_scene(cfg, ranges, strengths, snr_db, seed):
    """Simulate one record and process it (cached on all inputs)."""
    rng = np.random.default_rng(seed)
    rx, clean, d0 = simulate_rx(cfg, list(ranges), list(strengths), snr_db, rng=rng)
    return rx, d0, process(rx, cfg)


@st.cache_data(show_spinner=False)
def cached_curve(cfg, snrs, range_m, trials):
    return detection_curve(cfg, list(snrs), range_m=range_m, trials=trials, seed=7)


@st.cache_data(show_spinner=False)
def cached_windows(cfg):
    return [window_metrics(cfg, w) for w in WINDOW_NAMES]


@st.cache_data(show_spinner=False)
def cached_room(room, pos, snr_db, sep, seed):
    cfg = room_config()
    rx = simulate_room_record(cfg, room, pos, sep, (0.8, 0.8, 0.8, 0.8, 0.3, 0.4), snr_db,
                              np.random.default_rng(seed))
    return measure_room(rx, cfg, sep)


# ----------------------------------------------------------------- sidebar
st.sidebar.title("Settings")
mode = st.sidebar.radio("Mode", ["Simulation", "Live one-device"])
st.sidebar.caption("Both modes run the same matched filter + CFAR code.")

with st.sidebar.expander("Chirp", expanded=True):
    bw = st.slider("Bandwidth B (Hz)", 1000, 20000, 8000, 500)
    dur_ms = st.slider("Duration T (ms)", 2.0, 40.0, 10.0, 0.5)
    c_air = st.number_input("Speed of sound c (m/s)", 300.0, 360.0, C_AIR, 0.5)
    window = st.selectbox("Window on the matched filter", WINDOW_NAMES, index=2)
with st.sidebar.expander("CFAR detector", expanded=True):
    detector = st.radio("Type", ["os", "ca"], format_func=lambda k: {"os": "OS-CFAR (ordered statistic)",
                                                                 "ca": "CA-CFAR (cell averaging)"}[k], horizontal=False)
    n_train = st.slider("Training cells per side", 4, 40, 16)
    n_guard = st.slider("Guard cells per side", 0, 20, 8)
    log_pfa = st.slider("False-alarm probability Pfa (log10)", -8.0, -1.0, -4.0, 0.5)

if mode == "Simulation":
    with st.sidebar.expander("Scene", expanded=True):
        snr_db = st.slider("SNR (dB, per sample, direct sound)", -30, 30, -6)
        n_t = st.slider("Number of targets", 1, 5, 2)
        defaults = [1.2, 3.0, 4.5, 2.1, 5.5]
        t_ranges, t_str = [], []
        for i in range(n_t):
            c1, c2 = st.columns(2)
            t_ranges.append(c1.slider(f"Target {i + 1} distance (m)", 0.2, 8.0, defaults[i], 0.05, key=f"r{i}"))
            t_str.append(c2.slider(f"strength", 0.05, 1.0, [0.7, 0.5, 0.4, 0.6, 0.3][i], 0.05, key=f"s{i}"))
        if st.button("New noise sample"):
            st.session_state["seed"] = st.session_state.get("seed", 0) + 1
    seed = st.session_state.get("seed", 0)

f0 = 3000.0 if bw <= 19000 else 2000.0
max_r = max(t_ranges) if mode == "Simulation" else 6.0
record_s = max(0.06, 0.004 + 2 * max_r / c_air + dur_ms / 1000 + 0.012)
cfg = RadarConfig(f0=f0, bandwidth=float(bw), duration=dur_ms / 1000, record_s=round(record_s, 3), c=c_air,
                  window=window, detector=detector, n_train=n_train, n_guard=n_guard, pfa=10 ** log_pfa)

# ----------------------------------------------------------------- header
st.title("Finding echoes in noise: matched filter + CFAR")
st.write("The app sends a **chirp** (a tone sweeping up in pitch), listens, and looks for delayed copies of it. "
         "Comparing the recording with the known chirp (*matched filter*) makes each echo a sharp peak; "
         "a **CFAR** threshold then decides which peaks are real targets while keeping false alarms at a set rate.")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Range resolution c/(2B)", f"{cfg.resolution_m * 100:.2f} cm", help="Two targets closer than this merge into one peak")
k2.metric("Max unambiguous range c·PRI/2", f"{cfg.unambiguous_m:.1f} m",
          help="PRI = length of the listening window; an echo later than this would be mistaken for a closer one")
k3.metric("Time-bandwidth product B·T", f"{bw * dur_ms / 1000:.0f}", help="Larger = more noise suppression by pulse compression")
k4.metric("Processing gain", f"{10 * np.log10(cfg.duration * cfg.fs):.1f} dB",
          help="SNR improvement of the matched filter, 10·log10(number of chirp samples)")

# ----------------------------------------------------------------- get a record
true_ranges = None
rx = res = d0 = None
if mode == "Simulation":
    rx, d0, res = run_scene(cfg, tuple(t_ranges), tuple(t_str), snr_db, seed)
    true_ranges = list(t_ranges)
else:
    ok, msg = audio_status()
    if not ok:
        st.error(f"Live mode unavailable: {msg}. Showing the simulation instead — choose Simulation mode in the sidebar "
                 "or fix your audio devices and reload.")
        rx, d0, res = run_scene(cfg, (1.2, 3.0), (0.7, 0.5), -6, 0)
        true_ranges = [1.2, 3.0]
    else:
        st.info(f"Audio OK ({msg}). Put the laptop in the open, a flat hard surface facing it, turn the volume up, "
                "then press Record. The chirp is audible.")
        cfg = live_config(cfg, 0.4)
        if st.button("Record now", type="primary"):
            try:
                st.session_state["live_rx"] = record_with_playback(cfg)
            except AudioUnavailable as exc:
                st.error(str(exc))
        tape = st.number_input("Tape-measured distance to the surface (m, optional)", 0.0, 10.0, 0.0, 0.01)
        if "live_rx" in st.session_state:
            rx = st.session_state["live_rx"]
            res = process(rx, cfg)
            d0 = res.direct_index / cfg.fs if res.direct_index is not None else None
            true_ranges = [tape] if tape > 0 else None
        else:
            st.stop()

for w in res.warnings:
    st.warning("⚠️ " + w)

# ----------------------------------------------------------------- summary
tol = max(cfg.resolution_m, 0.02)
if true_ranges:
    rows, spurious = match_to_truth(true_ranges, res.det_range, tol)
    found = sum(d is not None for _, d in rows)
    errs = [abs(d - r) * 100 for r, d in rows if d is not None]
    msg = f"**Found {found} of {len(rows)} targets**" + (f", worst range error {max(errs):.1f} cm" if errs else "")
    msg += f"; {len(spurious)} extra detection(s) with no target (false alarm or sidelobe)."
    (st.success if found == len(rows) and not spurious else st.warning)(msg)
else:
    rows, spurious = [], list(res.det_range)
    st.info(f"{len(res.det_range)} echo(es) detected.")

t_ms = np.arange(len(rx)) / cfg.fs * 1000
rng_axis = (np.arange(len(rx)) - (res.direct_index or 0)) / cfg.fs * cfg.c / 2

# ----------------------------------------------------------------- 1. what was sent / came back
st.header("1. What was sent and what came back")
a, b = st.columns(2)
ref = cfg.reference()
fig, ax = plt.subplots(2, 1, figsize=(6, 4.2))
ax[0].plot(np.arange(len(ref)) / cfg.fs * 1000, ref, color=BLUE, lw=0.6)
ax[0].set(xlabel="time (ms)", ylabel="amplitude", title="Transmitted chirp")
ax[1].specgram(ref, NFFT=128, Fs=cfg.fs, noverlap=112, cmap="viridis")
ax[1].set(xlabel="time (s)", ylabel="frequency (Hz)", title=f"Its pitch sweeps {cfg.f0:.0f} → {cfg.f0 + bw:.0f} Hz", ylim=(0, 14000))
ax[1].grid(False)
fig.tight_layout()
a.pyplot(fig)
plt.close(fig)
fig, ax = plt.subplots(2, 1, figsize=(6, 4.2), sharex=True)
ax[0].plot(t_ms, rx, color=GREY, lw=0.4)
ax[0].set(ylabel="amplitude", title="Received signal (microphone): the echoes are hidden in the noise")
ax[1].plot(t_ms, res.env, color=BLUE, lw=0.8)
ax[1].set(xlabel="time (ms)", ylabel="matched-filter output", title="After the matched filter: echoes become peaks")
if res.direct_index is not None:
    ax[1].annotate("direct sound", (res.direct_index / cfg.fs * 1000, res.env.max()), xytext=(5, -2), textcoords="offset points",
                   color=GREY, fontsize=8)
fig.tight_layout()
b.pyplot(fig)
plt.close(fig)

# ----------------------------------------------------------------- 2. detection
st.header("2. Detections: matched-filter output vs CFAR threshold")
fig, ax = plt.subplots(figsize=(11, 3.8))
ax.plot(rng_axis, res.env, color=BLUE, lw=0.9, label="matched-filter output")
ax.plot(rng_axis, np.sqrt(np.where(np.isfinite(res.threshold), res.threshold, np.nan)), color=ORANGE, lw=1.4,
        label=f"{'OS' if detector == 'os' else 'CA'}-CFAR threshold (Pfa {cfg.pfa:.0e})")
if true_ranges:
    for r in true_ranges:
        ax.axvline(r, color=GREEN, lw=1, ls=":")
    ax.plot([], [], color=GREEN, ls=":", label="true target range")
xmax = min(cfg.unambiguous_m, max(max_r + 1.5, 3))
echo_part = res.env[(rng_axis > 0.1) & (rng_axis < xmax)]
ymax = 1.25 * max(echo_part.max() if len(echo_part) else 1, np.nanmax(np.sqrt(res.threshold[np.isfinite(res.threshold)])) if np.isfinite(res.threshold).any() else 1)
if len(res.det_range):
    ax.scatter(res.det_range, res.det_amp, color=RED, zorder=4, s=36, label="detected")
    for r, v in zip(res.det_range, res.det_amp):
        ax.annotate(f"{r:.2f} m", (r, v), xytext=(4, 5), textcoords="offset points", fontsize=8, color=RED)
ax.set(xlim=(-0.2, xmax), ylim=(0, ymax), xlabel="range from the device (m)  [relative to the direct sound at 0 m]",
       ylabel="amplitude")
ax.text(-0.15, ymax * 0.93, "direct sound\n(off scale)", fontsize=7, color=GREY, va="top")
ax.legend(loc="upper right", ncol=2)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

c1, c2 = st.columns([1.1, 1])
with c1:
    st.subheader("Detected vs true ranges")
    table = []
    for r, d in rows:
        table.append({"true range (m)": round(r, 3), "detected (m)": None if d is None else round(d, 3),
                      "error (cm)": None if d is None else round((d - r) * 100, 2),
                      "found": "✅" if d is not None else "❌ missed"})
    for d in spurious:
        table.append({"true range (m)": None, "detected (m)": round(float(d), 3), "error (cm)": None, "found": "⚠️ extra"})
    if not table:
        st.write("No detections.")
    else:
        st.dataframe(table, hide_index=True, width="stretch")
    if mode == "Simulation":
        st.caption("Per-target SNR = SNR + 20·log10(strength): " +
                   ", ".join(f"T{i + 1}: {snr_db + 20 * np.log10(s):.1f} dB" for i, s in enumerate(t_str)))
with c2:
    st.subheader("How CFAR sees one cell")
    centre = st.slider("Cell under test (range, m)", 0.1, float(min(cfg.unambiguous_m - 0.2, 8.0)),
                       float(res.det_range[0]) if len(res.det_range) else 1.0, 0.01)
    s = cfg.cell_stride
    cut = int(round((res.direct_index or 0) + range_to_delay(centre, cfg.c) * cfg.fs))
    cut = min(max(cut, 0), len(rx) - 1)
    offs = cfg.n_guard + 1 + s * np.arange(cfg.n_train)
    tr = np.concatenate([cut - offs, cut + offs])
    tr = tr[(tr >= 0) & (tr < len(rx))]
    gd = np.concatenate([np.arange(cut - cfg.n_guard, cut), np.arange(cut + 1, cut + cfg.n_guard + 1)])
    gd = gd[(gd >= 0) & (gd < len(rx))]
    width = int(cfg.n_guard + 1 + s * cfg.n_train + 10)
    lo, hi = max(cut - width, 0), min(cut + width, len(rx))
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    xs = np.arange(lo, hi)
    ax.plot(xs, res.env[lo:hi], color=GREY, lw=0.8)
    ax.plot(xs, np.sqrt(res.threshold[lo:hi]), color=ORANGE, lw=1.2, label="threshold")
    ax.scatter(tr, res.env[tr], color=GREEN, s=14, label="training cells", zorder=3)
    ax.scatter(gd, res.env[gd], color=ORANGE, s=10, label="guard cells (ignored)", zorder=3)
    ax.scatter([cut], res.env[[cut]], color=RED, marker="D", s=40, label="cell under test", zorder=4)
    ax.set(xlabel="sample", ylabel="amplitude")
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.caption("The threshold at the red cell = scale × the noise level estimated from the green cells "
               "(average for CA, k-th largest for OS). Move the slider across a target to see why neighbours matter.")

# ----------------------------------------------------------------- 3. windows
st.header("3. Sidelobes: windows trade a wider peak for cleaner skirts")
wm = cached_windows(cfg)
a, b = st.columns([1.3, 1])
fig, ax = plt.subplots(figsize=(7, 3.4))
from src.chirp import chirp_at  # noqa: E402
for w, col in zip(WINDOW_NAMES, (GREY, BLUE, ORANGE)):
    c_w = replace(cfg, window=w, record_s=0.03)
    env_w, _ = matched_power(chirp_at(np.arange(c_w.n_samples) / c_w.fs - 0.01, c_w.f0, c_w.bandwidth, c_w.duration), c_w)
    x = (np.arange(len(env_w)) - 0.01 * c_w.fs) / c_w.fs * c_w.c / 2 * 100
    ax.plot(x, 20 * np.log10(np.maximum(env_w / env_w.max(), 1e-6)), color=col, lw=1, label=w)
ax.set(xlim=(-30, 30), ylim=(-70, 3), xlabel="range offset (cm)", ylabel="dB re peak",
       title="One target, three windows (your current B and T)")
ax.legend(loc="upper right")
fig.tight_layout()
a.pyplot(fig)
plt.close(fig)
b.dataframe([{"window": m["window"], "PSLR (dB)": round(m["pslr_db"], 1), "−3 dB width (cm)": round(m["width3db_m"] * 100, 2),
              "SNR loss (dB)": round(m["snr_loss_db"], 2)} for m in wm], hide_index=True, width="stretch")
b.caption("PSLR = peak sidelobe level: how tall the biggest false skirt is relative to the real peak (lower is better). "
          "A strong echo with a rectangular window leaves a −13 dB skirt that can hide weak neighbours.")

# ----------------------------------------------------------------- 4. Monte Carlo
st.header("4. How reliable is this setting? Probability of detection vs SNR")
mc_range = st.slider("Target distance for this test (m)", 0.5, 6.0, 1.5, 0.1)
full = st.button("Run full Monte Carlo (500 trials, slower)")
trials = 500 if full else 40
snrs = tuple(np.arange(-22, -3, 2.0))
with st.spinner(f"Monte Carlo, {trials} trials per point..."):
    curves = {d: cached_curve(replace(cfg, detector=d), snrs, mc_range, trials) for d in ("ca", "os")}
fig, ax = plt.subplots(figsize=(7, 3.4))
for d, col, nm in (("ca", ORANGE, "CA-CFAR"), ("os", BLUE, "OS-CFAR")):
    ax.plot(curves[d]["snr_db"], curves[d]["pd"], "o-", color=col, ms=3.5, label=nm)
if mode == "Simulation":
    ax.axvline(snr_db + 20 * np.log10(min(t_str)), color=GREEN, ls=":", label="weakest target's SNR now")
ax.set(xlabel="SNR of the target (dB per sample)", ylabel="probability of detection", ylim=(-0.03, 1.03),
       title=f"{trials} trials per point" + ("" if full else " (quick; press the button for 500)"))
ax.legend(loc="lower right")
fig.tight_layout()
a, b = st.columns([1.3, 1])
a.pyplot(fig)
plt.close(fig)
b.write("Each point is the fraction of simulated noise records in which the target was found at the "
        "detector's current settings. With quick mode (40 trials) points wobble by about ±0.1.")

# ----------------------------------------------------------------- 5. room
st.header("5. Optional: room length and breadth")
st.caption("Limits: rectangular, empty room; laptop in the open with its speaker–microphone line parallel to a wall; "
           "no furniture; height is **not** estimated. Results are wrong near corners, with strong furniture echoes, "
           "or when the far-wall echoes sink into noise. One microphone cannot tell left from right, so walls are "
           "reported as nearer / farther.")
with st.expander("Room-size panel (simulated room)", expanded=True):
    r1, r2, r3 = st.columns(3)
    L = r1.slider("True length (m)", 4.0, 9.0, 6.0, 0.1)
    W = r1.slider("True breadth (m)", 3.0, 8.0, 4.0, 0.1)
    px = r2.slider("Laptop position along breadth (fraction)", 0.25, 0.75, 0.45, 0.05)
    py = r2.slider("Laptop position along length (fraction)", 0.25, 0.75, 0.4, 0.05)
    rsnr = r3.slider("SNR of the direct sound (dB)", 20, 70, 50)
    sep = r3.slider("Speaker–mic distance (m)", 0.05, 0.4, 0.2, 0.05)
    if st.button("Estimate room size"):
        # the "front/back" axis is the one along the speaker-mic line: use the length for it
        est = cached_room((W, L, 2.7), (px * W, py * L, 1.0), rsnr, sep, 1)
        if not est["ok"]:
            st.error("Could not estimate: " + est.get("reason", "unknown"))
        else:
            if not est["confident"]:
                st.warning("Low confidence: fewer than 60 % of detected echoes are explained by the best room model.")
            m1, m2 = st.columns(2)
            m1.metric("Estimated length", f"{est['length']:.2f} m", f"{est['length'] - max(L, W):+.2f} vs true")
            m2.metric("Estimated breadth", f"{est['breadth']:.2f} m", f"{est['breadth'] - min(L, W):+.2f} vs true")
            fig, ax = plt.subplots(figsize=(5.5, 4.2))
            draw_room(ax, est, truth=(W, L, (px * W, py * L)))
            fig.tight_layout()
            m1.pyplot(fig)
            plt.close(fig)
            lr, fb = est["left_right"], est["front_back"]
            m2.write(f"Laptop is **{min(lr):.2f} m** from the nearer side wall and **{max(lr):.2f} m** from the farther; "
                     f"**{min(fb):.2f} m** from the nearer front/back wall and **{max(fb):.2f} m** from the farther.")
            m2.write(f"Echoes detected and explained: {est['echoes_explained']} of {est['echoes_total']} strongest.")
