from matplotlib.patches import FancyBboxPatch
from common import BLUE, GREEN, GREY, ORANGE, plt, save_fig

fig, ax = plt.subplots(figsize=(11, 3.6)); ax.set_xlim(0, 11); ax.set_ylim(0, 3.6); ax.axis("off")
def box(x, y, w, h, t, c):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", fc=c, ec="none", alpha=0.18))
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", fc="none", ec=c, lw=1.6))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8.6)
def arr(x0, y0, x1, y1): ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.3))
box(0.1, 2.2, 2.0, 1.1, "ESC-50\nzip / folder / GitHub\n+ meta/esc50.csv", GREY)
box(2.6, 2.2, 2.2, 1.1, "Preprocess\nmono, 16 kHz, peak-normalise,\ntrim silent padding", BLUE)
box(5.3, 2.2, 2.4, 1.1, "Build test recording\nclips joined by 1 s silence;\nexact spans = ground truth", ORANGE)
box(8.2, 2.2, 2.6, 1.1, "Template = one clip\n(fold 1) of the chosen class", BLUE)
for x0, x1 in ((2.1, 2.6), (4.8, 5.3)): arr(x0, 2.75, x1, 2.75)
arr(8.2, 2.75, 7.7, 2.75)
box(1.4, 0.3, 2.6, 1.2, "FFT normalised\ncross-correlation\n(window-energy normalised)", BLUE)
box(4.5, 0.3, 2.4, 1.2, "Threshold + peak picking\n(non-maximum suppression)", BLUE)
box(7.4, 0.3, 3.2, 1.2, "Score: centre inside true span?\nprecision, recall, F1; best threshold", GREEN)
arr(6.5, 2.2, 3.2, 1.5); arr(4.0, 0.9, 4.5, 0.9); arr(6.9, 0.9, 7.4, 0.9)
save_fig(fig, "fig_flow.png")
