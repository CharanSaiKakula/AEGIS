import matplotlib.pyplot as plt
import numpy as np

# Exact arrays provided
years = np.arange(2015, 2024)
sexual_assault = np.array([26, 26, 27, 32, 32, 23, 28, 41, 63])
stalking = np.array([15, 9, 9, 12, 14, 8, 17, 9, 25])
aggravated_assault = np.array([6, 8, 4, 0, 2, 10, 2, 3, 13])

# Exact output requirement: 1920×1080 at 300 DPI
dpi = 300
width_px, height_px = 1920, 1080
figsize = (width_px / dpi, height_px / dpi)  # inches

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.titlesize": 20,
    "axes.labelsize": 16,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

# Required colors (colorblind-friendly Matplotlib tab palette)
c_blue   = "#1f77b4"
c_orange = "#ff7f0e"
c_green  = "#2ca02c"

# Lines with required markers + 2–3 px linewidth
ax.plot(
    years, sexual_assault,
    label="Sexual assault (rape+fondling)",
    color=c_blue, linewidth=2.5,
    marker="o", markersize=6
)
ax.plot(
    years, stalking,
    label="Stalking",
    color=c_orange, linewidth=2.5,
    marker="s", markersize=6
)
ax.plot(
    years, aggravated_assault,
    label="Aggravated assault",
    color=c_green, linewidth=2.5,
    marker="^", markersize=6
)

# Title and axes (exact text + required y-range/ticks)
ax.set_title("CU Boulder Clery counts (calendar years 2015–2023)")
ax.set_xlabel("Year", labelpad=10)
ax.set_ylabel("Incidents (count)")

ax.set_xticks(years)
ax.set_xlim(2014.6, 2023.4)

ax.set_ylim(0, 70)
ax.set_yticks(np.arange(0, 71, 10))

# Gridlines
ax.grid(True, which="major", linestyle="-", linewidth=0.8, alpha=0.25)

# Legend upper-left with frame
ax.legend(loc="upper left", frameon=True)

# Annotate ONLY 2023 points with rounded boxes; offsets chosen to avoid overlap
final_year = 2023
final_idx = int(np.where(years == final_year)[0][0])

def annotate_final(yvals, color, offset_points):
    ax.annotate(
        f"{int(yvals[final_idx])}",
        xy=(final_year, yvals[final_idx]),
        xytext=offset_points,
        textcoords="offset points",
        ha="left",
        va="center",
        fontsize=12,
        color=color,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=1, alpha=0.9),
        arrowprops=dict(arrowstyle="-", color=color, lw=1, alpha=0.8),
    )

annotate_final(sexual_assault, c_blue, (10, 0))
annotate_final(stalking, c_orange, (10, 10))
annotate_final(aggravated_assault, c_green, (10, -10))

# Leave space for caption; prevent clipping
fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.28)

# Caption below chart (exact text)
fig.text(
    0.5, 0.08,
    "Source: CU Boulder ASFSR Clery tables (2015–2023).",
    ha="center", va="center", fontsize=12
)

# Export (no bbox_inches='tight' to preserve exact 1920×1080 px)
fig.savefig("cu_boulder_clery_counts_2015_2023_1920x1080.png", dpi=dpi)
fig.savefig("cu_boulder_clery_counts_2015_2023.svg", format="svg")

plt.show()
