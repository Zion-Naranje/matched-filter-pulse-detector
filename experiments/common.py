"""Shared helpers for the experiment scripts (paths, plot style, table writer)."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG = ROOT / "docs" / "figures"
TAB = ROOT / "docs" / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

# colour-blind-safe palette
BLUE, ORANGE, GREEN, GREY, RED = "#0072B2", "#D55E00", "#009E73", "#6b6b6b", "#CC3311"
WIN_COLOR = {"rectangular": GREY, "hamming": BLUE, "taylor": ORANGE}
DET_COLOR = {"ca": ORANGE, "os": BLUE}
DET_NAME = {"ca": "CA-CFAR", "os": "OS-CFAR"}

plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 170, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "legend.frameon": False})


def save_fig(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)
    print("figure ->", FIG / name)


def write_table(name, header, rows):
    """Write docs/tables/<name>.csv exactly as computed (no rounding beyond formatting)."""
    with open(TAB / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print("table  ->", TAB / f"{name}.csv")


def update_results(key, value):
    """Merge a result block into docs/tables/results.json (read by the report builder)."""
    p = TAB / "results.json"
    data = json.loads(p.read_text()) if p.exists() else {}
    data[key] = value
    p.write_text(json.dumps(data, indent=2, default=float))
