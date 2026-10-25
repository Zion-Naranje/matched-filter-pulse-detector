"""Methodology flow chart (report section 4 and the deck)."""
from matplotlib.patches import FancyBboxPatch

from common import BLUE, GREEN, GREY, ORANGE, plt, save_fig

fig, ax = plt.subplots(figsize=(11, 4.6))
ax.set_xlim(0, 11)
ax.set_ylim(0, 4.6)
ax.axis("off")


def box(x, y, w, h, text, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                fc=color, ec="none", alpha=0.18))
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                fc="none", ec=color, lw=1.6))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.6)


def arrow(x0, y0, x1, y1):
    ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.3))


top = 3.2
box(0.1, top, 1.9, 1.0, "1. Chirp generator\nf0, bandwidth B,\nduration T, fs", BLUE)
box(2.5, top, 1.9, 1.0, "2. Scene\nSimulation: echoes + noise\nLive: speaker -> mic", ORANGE)
box(4.9, top, 1.9, 1.0, "3. Matched filter\nFFT correlation with\nwindowed reference", BLUE)
box(7.3, top, 1.9, 1.0, "4. CFAR threshold\nCA-CFAR or OS-CFAR\n(set by Pfa)", BLUE)
box(9.5, top, 1.4, 1.0, "5. Peak picking\nrange = c t / 2", BLUE)
for x in (2.0, 4.4, 6.8, 9.2):
    arrow(x + 0.05, top + 0.5, x + 0.45, top + 0.5)
box(0.1, 1.5, 3.2, 1.0, "Live mode only: strongest peak = direct\nspeaker->mic sound = zero distance\n(cancels unknown audio latency)", GREEN)
box(3.7, 1.5, 3.2, 1.0, "Metrics (Monte Carlo)\nPd vs SNR, false alarms, range error,\nPSLR and main-lobe width per window", GREEN)
box(7.3, 1.5, 3.6, 1.0, "Optional: room length & breadth\nimage-source simulation, wall echoes\npaired into 2 axes", GREEN)
box(0.1, 0.1, 10.8, 0.9, "Outputs: Streamlit app (plots, detected-vs-true table, Pd curve)  |  report figures and tables  |  pytest suite", GREY)
arrow(3.45, top, 1.7, 2.55)
arrow(6.2, top, 5.3, 2.55)
arrow(8.5, top, 8.9, 2.55)
for x in (1.7, 5.3, 9.1):
    arrow(x, 1.5, x, 1.05)
save_fig(fig, "fig_flowchart.png")
