"""Experiment 7: room length and breadth from simulated recordings (image-source model).

Truth is known, so we report every success AND failure.  Success = both dimensions within 5 cm.
"""
import numpy as np

from common import BLUE, GREEN, GREY, ORANGE, RED, plt, save_fig, update_results, write_table
from src.room import measure_room, room_config, simulate_room_record

BETA = (0.8, 0.8, 0.8, 0.8, 0.3, 0.4)        # walls 0.8, floor 0.3 (carpet), ceiling 0.4
SEP = 0.2                                    # speaker-microphone separation, m
cfg = room_config()
TOL = 0.05
rooms = [(4.0, 3.0, 2.6), (5.0, 4.0, 2.7), (6.0, 4.0, 2.7), (7.0, 5.0, 3.0), (8.0, 5.5, 3.0), (9.0, 6.0, 3.2)]
SNRS = [60, 50, 40, 30, 20]                  # SNR of the direct sound; echoes are ~26-45 dB weaker
POS_PER_ROOM = 6
rng = np.random.default_rng(2024)

table, store = [], {}
example_ok = example_bad = None
for snr in SNRS:
    ok_all = 0
    n_all = 0
    for room in rooms:
        good, errs_l, errs_b, n_ok = 0, [], [], 0
        for k in range(POS_PER_ROOM):
            pos = (rng.uniform(0.25, 0.75) * room[0], rng.uniform(0.25, 0.75) * room[1], rng.uniform(0.8, 1.2))
            rx = simulate_room_record(cfg, room, pos, SEP, BETA, snr, rng)
            e = measure_room(rx, cfg, SEP)
            n_all += 1
            if not e["ok"]:
                continue
            n_ok += 1
            el, eb = e["length"] - max(room[:2]), e["breadth"] - min(room[:2])
            if abs(el) <= TOL and abs(eb) <= TOL:
                good += 1
                errs_l.append(abs(el))
                errs_b.append(abs(eb))
            if snr == 50:
                ok_ = abs(el) <= TOL and abs(eb) <= TOL
                if ok_ and example_ok is None and room == rooms[2]:
                    example_ok = (room, pos, e)
                if not ok_ and example_bad is None:
                    example_bad = (room, pos, e)
        ok_all += good
        table.append([f"{room[0]:.1f} x {room[1]:.1f} x {room[2]:.1f}", snr, POS_PER_ROOM, n_ok, good,
                      f"{100 * np.mean(errs_l):.1f}" if errs_l else "n/a",
                      f"{100 * np.mean(errs_b):.1f}" if errs_b else "n/a"])
    store[snr] = ok_all / n_all
    print(f"SNR {snr} dB: {ok_all}/{n_all} within {TOL * 100:.0f} cm")
write_table("room_estimates", ["room_true_LxWxH_m", "direct_SNR_dB", "positions", "estimate_returned",
                               "both_dims_within_5cm", "mean_abs_err_length_cm", "mean_abs_err_breadth_cm"], table)

# Wider random sweep at 50 dB
n, good, big = 100, 0, []
for _ in range(n):
    L = rng.uniform(4, 9); W = rng.uniform(3, L); H = rng.uniform(2.5, 3.2)
    pos = (rng.uniform(0.25, 0.75) * L, rng.uniform(0.25, 0.75) * W, rng.uniform(0.8, 1.2))
    e = measure_room(simulate_room_record(cfg, (L, W, H), pos, SEP, BETA, 50, rng), cfg, SEP)
    if e["ok"]:
        el, eb = e["length"] - max(L, W), e["breadth"] - min(L, W)
        good += abs(el) <= TOL and abs(eb) <= TOL
        big.append((abs(el), abs(eb)))
big = np.array(big)
print(f"random sweep at 50 dB: {good}/{n} within 5 cm; median abs err length {100 * np.median(big[:, 0]):.1f} cm, "
      f"breadth {100 * np.median(big[:, 1]):.1f} cm")
update_results("room", dict(tolerance_m=TOL, success_vs_snr=store, sweep_n=n, sweep_success=int(good),
                            sweep_median_err_length_cm=100 * float(np.median(big[:, 0])),
                            sweep_median_err_breadth_cm=100 * float(np.median(big[:, 1])),
                            beta=BETA, sep_m=SEP, rooms=rooms, positions_per_room=POS_PER_ROOM))

# Figure: top-down map of one success and one failure + success rate vs SNR
from src.plots import draw_room

fig, ax = plt.subplots(1, 3, figsize=(14, 4.8), gridspec_kw=dict(width_ratios=[1.15, 1.15, 0.9]))
for a_, (kind, ex) in zip(ax[:2], (("success", example_ok), ("failure", example_bad))):
    room, pos, e = ex
    draw_room(a_, e, truth=(room[0], room[1], (pos[0], pos[1])))
    a_.set_title(f"A {kind} (direct SNR 50 dB)\nestimate {e['length']:.2f} x {e['breadth']:.2f} m; "
                 f"true {max(room[:2]):.2f} x {min(room[:2]):.2f} m", fontsize=9.5)
ax[2].bar([str(s) for s in SNRS], [100 * store[s] for s in SNRS], color=BLUE)
for i, s in enumerate(SNRS):
    ax[2].text(i, 100 * store[s] + 1.5, f"{100 * store[s]:.0f}%", ha="center", fontsize=9)
ax[2].set(xlabel="SNR of the direct sound (dB)", ylabel="% of rooms within 5 cm", ylim=(0, 112),
          title=f"Success rate ({len(rooms) * POS_PER_ROOM} rooms/positions per bar)")
save_fig(fig, "fig7_room.png")
