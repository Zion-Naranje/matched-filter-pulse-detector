"""Experiment 6: live one-device run against a tape-measured wall/box.

Usage:  python experiments/exp6_live.py --distance 1.00 [--runs 5]
Place the laptop in the open, a hard flat surface (wall, large box) facing the speaker/mic at a
tape-measured distance (laptop edge to surface, metres).  Without an audio device the script
writes a clearly marked PLACEHOLDER table instead of inventing numbers.
"""
import argparse

import numpy as np

from common import update_results, write_table
from src.audio_io import audio_status, live_config, record_with_playback, AudioUnavailable
from src.pipeline import RadarConfig, process

ap = argparse.ArgumentParser()
ap.add_argument("--distance", type=float, default=None, help="tape-measured distance in metres")
ap.add_argument("--runs", type=int, default=5)
ap.add_argument("--sep", type=float, default=0.0, help="speaker-microphone separation (m), optional")
args = ap.parse_args()

HEADER = ["run", "tape_distance_m", "measured_range_m", "error_cm", "direct_peak_snr_dB", "note"]
ok, msg = audio_status()
if not ok or args.distance is None:
    reason = msg if not ok else "no --distance given"
    print("LIVE RUN NOT PERFORMED:", reason)
    write_table("live_run", HEADER, [[i + 1, "TBD", "TBD", "TBD", "TBD", f"PLACEHOLDER - {reason}"]
                                     for i in range(args.runs)])
    update_results("live", dict(performed=False, reason=reason))
    raise SystemExit(0)

cfg = live_config(RadarConfig(), 0.4)
rows, errs = [], []
for i in range(args.runs):
    try:
        rx = record_with_playback(cfg)
    except AudioUnavailable as exc:
        print("audio failed:", exc)
        break
    res = process(rx, cfg)
    if not res.direct_ok or len(res.det_range) == 0:
        rows.append([i + 1, args.distance, "none", "n/a", f"{res.direct_snr_db:.1f}", "; ".join(res.warnings) or "no echo"])
        continue
    j = int(np.argmin(np.abs(res.det_range + args.sep / 2 - args.distance)))
    r = float(res.det_range[j] + args.sep / 2)
    errs.append(r - args.distance)
    rows.append([i + 1, args.distance, f"{r:.4f}", f"{100 * (r - args.distance):.1f}", f"{res.direct_snr_db:.1f}", ""])
write_table("live_run", HEADER, rows)
if errs:
    update_results("live", dict(performed=True, distance_m=args.distance, errors_cm=[100 * e for e in errs],
                                mean_error_cm=100 * float(np.mean(errs)), std_error_cm=100 * float(np.std(errs))))
    print(f"mean error {100 * np.mean(errs):.1f} cm, std {100 * np.std(errs):.1f} cm over {len(errs)} runs")
