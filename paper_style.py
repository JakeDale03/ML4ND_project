from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

# Colourblind-friendly palette (based on Wong 2011, Nature Methods)
COLORS = {
    "blue":   "#0072B2",
    "orange": "#E69F00",
    "green":  "#009E73",
    "red":    "#D55E00",
    "purple": "#CC79A7",
    "sky":    "#56B4E9",
    "yellow": "#F0E442",
    "black":  "#000000",
}

# Ordered list for cycling
COLOR_CYCLE = [
    COLORS["blue"],
    COLORS["orange"],
    COLORS["green"],
    COLORS["red"],
    COLORS["purple"],
    COLORS["sky"],
    COLORS["yellow"],
    COLORS["black"],
]

# Size presets
FIGURE_SIZES = {
    "single":   (3.375, 2.531),   # single column, 4:3 aspect
    "double":   (6.875, 2.531),   # two columns side-by-side
    "square":   (3.375, 3.375),   # single column, square
    "full":     (7.0,   5.25),    # full page width
    "wide":     (6.875, 4.0),     # double-width, slightly taller
}

DEFAULT_SIZE = "single"


def apply_paper_style(
    fig_size: str | tuple = DEFAULT_SIZE,
    font_size: float = 8.0,
    line_width: float = 1.0,
    marker_size: float = 3.0,
    use_latex: bool = False,
) -> None:
    if isinstance(fig_size, str):
        if fig_size not in FIGURE_SIZES:
            raise ValueError(f"Unknown fig_size preset '{fig_size}'. "
                             f"Choose from: {list(FIGURE_SIZES)}")
        fig_size = FIGURE_SIZES[fig_size]

    params = {
        # Figure
        "figure.figsize":        fig_size,
        "figure.dpi":            150,
        "savefig.dpi":           300,
        "savefig.bbox":          "tight",
        "savefig.pad_inches":    0.02,

        # Font
        "font.family":           "serif" if use_latex else "sans-serif",
        "font.size":             font_size,
        "axes.titlesize":        font_size + 1,
        "axes.labelsize":        font_size,
        "xtick.labelsize":       font_size - 1,
        "ytick.labelsize":       font_size - 1,
        "legend.fontsize":       font_size - 1,
        "legend.title_fontsize": font_size,

        # LaTeX
        "text.usetex":           use_latex,
        "mathtext.fontset":      "stix",

        # Lines & markers
        "lines.linewidth":       line_width,
        "lines.markersize":      marker_size,

        # Axes
        "axes.linewidth":        line_width * 0.8,
        "axes.spines.top":       False,
        "axes.spines.right":     False,
        "axes.prop_cycle":       mpl.cycler(color=COLOR_CYCLE),
        "axes.grid":             True,
        "axes.axisbelow":        True,

        # Grid
        "grid.linewidth":        0.5,
        "grid.alpha":            0.4,
        "grid.color":            "#AAAAAA",
        "grid.linestyle":        "--",

        # Ticks
        "xtick.direction":       "in",
        "ytick.direction":       "in",
        "xtick.major.width":     line_width * 0.8,
        "ytick.major.width":     line_width * 0.8,
        "xtick.minor.visible":   True,
        "ytick.minor.visible":   True,
        "xtick.minor.width":     line_width * 0.5,
        "ytick.minor.width":     line_width * 0.5,

        # Legend
        "legend.frameon":        True,
        "legend.framealpha":     0.8,
        "legend.edgecolor":      "0.8",
        "legend.borderpad":      0.4,
        "legend.handlelength":   1.5,

        # Saving
        "pdf.fonttype":          42,
        "ps.fonttype":           42,
    }

    mpl.rcParams.update(params)


# Apply on import
apply_paper_style()


# Convenience helpers
def fig(size: str | tuple = DEFAULT_SIZE, **kwargs):

    # Create a figure pre-sized to a named preset.
    if isinstance(size, str):
        size = FIGURE_SIZES[size]
    return plt.subplots(figsize=size, **kwargs)


def save(path: str, fig=None, **kwargs):

    # Save a figure with journal-safe defaults (300 dpi, tight bbox, PDF fonts).
    target = fig or plt.gcf()
    target.savefig(path, dpi=300, bbox_inches="tight", **kwargs)
    print(f"Saved to {path}")
