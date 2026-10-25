#!/usr/bin/env bash
# Regenerate every figure and table in docs/ (takes a few minutes).
set -e
cd "$(dirname "$0")"
for f in exp1_windows exp3_4_detection exp5_masking exp6_live exp7_room exp8_new_settings exp9_guard_sweep fig_cfar_geometry fig_flowchart; do
  echo "== $f"; python $f.py
done
