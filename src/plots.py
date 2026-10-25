"""Plot helpers shared by the Streamlit app and the experiment scripts (matplotlib)."""
import numpy as np
from matplotlib.patches import Rectangle

BLUE, ORANGE, GREEN, GREY, RED = "#0072B2", "#D55E00", "#009E73", "#6b6b6b", "#CC3311"


def draw_room(ax, est, truth=None):
    """Top view of the estimated room (and, in simulation, the true one).

    est   : dict from estimate_room (left_right, front_back are sorted nearer->farther wall).
    truth : optional (Lx, Ly, (x, y)) of the simulated room and laptop position.
    One omni microphone cannot tell left from right, so both rooms are drawn with the nearer
    wall on the left / bottom.
    """
    lr, fb = est["left_right"], est["front_back"]
    w, h = sum(lr), sum(fb)
    if truth is not None:
        lx, ly, (px, py) = truth
        tw, th = lx, ly
        tpos = (min(px, lx - px), min(py, ly - py))
        ax.add_patch(Rectangle((0, 0), tw, th, fill=False, ec=GREY, lw=3, label="true room"))
        ax.scatter(*tpos, marker="s", s=70, color=GREY, zorder=3, label="true laptop position")
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, ec=ORANGE, lw=2, ls="--", label="estimated room"))
    ax.scatter([lr[0]], [fb[0]], marker="s", s=40, color=BLUE, zorder=4, label="estimated laptop position")
    for (dx, dy) in ((-lr[0], 0), (lr[1], 0), (0, -fb[0]), (0, fb[1])):
        ax.annotate("", (lr[0] + dx, fb[0] + dy), (lr[0], fb[0]),
                    arrowprops=dict(arrowstyle="<->", color=GREEN, lw=1.1))
        ax.text(lr[0] + dx / 2, fb[0] + dy / 2, f"{abs(dx + dy):.2f} m", color=GREEN, fontsize=8,
                ha="center", va="bottom", bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.5))
    m = 0.6
    X = max(w, truth[0] if truth else 0)
    Y = max(h, truth[1] if truth else 0)
    ax.set(xlim=(-m, X + m), ylim=(-m, Y + m), aspect="equal", xlabel="metres (left-right)",
           ylabel="metres (front-back)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=8, frameon=False)
