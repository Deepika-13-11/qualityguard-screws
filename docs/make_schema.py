import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(13, 6.2))
ax.set_xlim(0, 13); ax.set_ylim(-0.1, 6.2); ax.axis("off")

def box(x, y, w, h, title, body, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=color, ec="#333", lw=1.4))
    ax.text(x + w / 2, y + h - 0.3, title, ha="center", va="center", fontsize=10.5, fontweight="bold")
    ax.text(x + w / 2, y + (h - 0.3) / 2, body, ha="center", va="center", fontsize=8.3)

def arrow(x1, y1, x2, y2, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.6, color="#333"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, label, ha="center", fontsize=8, style="italic")

ax.text(6.5, 5.85, "QualityGuard AI - Agent Architecture (Observe -> Reason -> Act -> Remember)",
        ha="center", fontsize=13, fontweight="bold")

box(0.2, 3.1, 2.3, 1.8, "INPUT", "CMM measurements\n(data/*.csv)\n+ specs.json\n(ISO 4762 limits)", "#e8f1ff")
box(3.1, 3.1, 2.3, 1.8, "1. OBSERVE", "read_cmm_csv()\nvalidate columns\nload memory", "#fff4d6")
box(6.0, 3.1, 2.6, 1.8, "2. REASON (tools)", "calculate_stats()\ncalculate_cpk()\ncheck_tolerance()\ndetect_trend()", "#ffe3e3")
box(9.2, 3.1, 2.3, 1.8, "3. ACT", "status per feature\nbatch disposition\ncorrective action", "#e3f7e3")
box(11.7, 3.1, 1.2, 1.8, "OUTPUT", "console\nJSON\nchart", "#e8f1ff")

box(3.1, 0.4, 2.3, 1.6, "MEMORY", "memory/history.json\npast batches:\nmean, Cpk, defects", "#f0e6ff")
box(6.0, 0.4, 2.6, 1.6, "LLM (optional)", "Claude API\nroot-cause\nexplanation", "#f0e6ff")
box(9.2, 0.4, 2.3, 1.6, "4. REMEMBER", "save batch result\nfor trend detection", "#fff4d6")

arrow(2.5, 4.0, 3.1, 4.0); arrow(5.4, 4.0, 6.0, 4.0); arrow(8.6, 4.0, 9.2, 4.0); arrow(11.5, 4.0, 11.7, 4.0)
arrow(4.25, 2.0, 4.25, 3.1, "history")
arrow(7.3, 2.0, 7.3, 3.1, "explain")
arrow(10.35, 3.1, 10.35, 2.0)
ax.plot([10.35, 10.35, 4.25], [0.4, 0.05, 0.05], color="#333", lw=1.6)
ax.annotate("", xy=(4.25, 0.4), xytext=(4.25, 0.05), arrowprops=dict(arrowstyle="->", lw=1.6, color="#333"))
ax.text(7.3, 0.12, "update memory", ha="center", fontsize=8, style="italic")
fig.savefig("docs/schema.png", dpi=130, bbox_inches="tight")
