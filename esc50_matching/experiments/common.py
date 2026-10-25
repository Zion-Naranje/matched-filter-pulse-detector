import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG, TAB = ROOT / "docs" / "figures", ROOT / "docs" / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, GREEN, GREY, RED = "#0072B2", "#D55E00", "#009E73", "#6b6b6b", "#CC3311"
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 170, "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "legend.frameon": False})


def save_fig(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)
    print("figure ->", FIG / name)


def write_table(name, header, rows):
    with open(TAB / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print("table  ->", TAB / f"{name}.csv")


def update_results(key, value):
    p = TAB / "results.json"
    d = json.loads(p.read_text()) if p.exists() else {}
    d[key] = value
    p.write_text(json.dumps(d, indent=2, default=float))
