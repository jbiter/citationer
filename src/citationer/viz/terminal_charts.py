"""Terminal-native chart rendering via plotext.

Provides chart functions for stats command visualisation.
Each function renders directly to stdout and returns True on success.
"""

from __future__ import annotations

import re
import sys

# ── style constants ────────────────────────────────────────────────
_LINE_COLOR = 6       # cyan
_BAR_COLOR = 4        # blue
_CUMULATIVE_COLOR = 3  # gold
_LINE_WIDTH = 78
_BAR_WIDTH = 80

# Matches ALL ANSI SGR sequences (color, style, reset)
_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")


def _can_render() -> bool:
    """Return True if stdout is a real terminal and plotext is available."""
    if not sys.stdout.isatty():
        return False
    try:
        import plotext  # noqa: F401
        return True
    except ImportError:
        return False


def _show(chart: str) -> None:
    """Print chart to stdout, stripping all ANSI color codes.

    With all SGR sequences removed the chart inherits the terminal's
    current text colour — white on dark backgrounds, black on light
    backgrounds — blending seamlessly into the user's theme.
    """
    clean = _SGR_RE.sub("", chart)
    print(clean, end="")


# ── line chart ─────────────────────────────────────────────────────


def plot_line(
    years: list[int],
    counts: list[int],
    *,
    title: str = "Publication Trend",
    xlabel: str = "Year",
    ylabel: str = "Publications",
) -> bool:
    """Render a braille line chart.  Returns True on success."""
    if not _can_render() or not years:
        return False

    import plotext as plt

    plt.clf()
    plt.plotsize(_LINE_WIDTH, min(18, len(years) + 4))

    plt.plot(years, counts, marker="braille", color=_LINE_COLOR)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True)

    _show(plt.build())
    return True


def plot_line_dual(
    years: list[int],
    counts: list[int],
    cumulative: list[int],
    *,
    title: str = "Publication Trend (with Cumulative)",
) -> bool:
    """Bars (annual) + braille line (cumulative).  Returns True on success."""
    if not _can_render() or not years:
        return False

    import plotext as plt

    plt.clf()
    plt.plotsize(_LINE_WIDTH, min(18, len(years) + 4))

    plt.bar(years, counts, color=_BAR_COLOR, label="Annual")
    plt.xlabel("Year")
    plt.ylabel("Publications", color=_BAR_COLOR)
    plt.tick_params(axis="y", color=_BAR_COLOR)

    plt.twinx()
    plt.plot(years, cumulative, marker="braille", color=_CUMULATIVE_COLOR, label="Cumulative")
    plt.ylabel("Cumulative", color=_CUMULATIVE_COLOR)
    plt.tick_params(axis="y", color=_CUMULATIVE_COLOR)

    plt.title(title)
    plt.grid(True)

    _show(plt.build())
    return True


# ── horizontal bar chart ───────────────────────────────────────────


def plot_hbar(
    labels: list[str],
    values: list[int],
    *,
    title: str = "Ranking",
    max_items: int = 20,
) -> bool:
    """Render a horizontal bar chart.

    Each bar is one plotext row; labels show the count in parentheses.
    Chart is capped at 12 visible bars to fit a standard terminal.

    Returns True on success.
    """
    if not _can_render() or not labels:
        return False

    import plotext as plt

    # Cap bar count so the chart fits in a ~24-line terminal window.
    # plotext renders each hbar as 2 character rows.
    limit = min(len(labels), max_items, 12)

    items = list(zip(labels[:limit], values[:limit]))

    display_labels: list[str] = []
    display_values: list[int] = []
    for i, (lbl, val) in enumerate(items):
        short = (lbl[:22] + "…") if len(lbl) > 24 else lbl
        display_labels.append(f"{short} ({val})")
        display_values.append(val)
        if i < len(items) - 1:
            display_labels.append(" ")
            display_values.append(0)

    display_labels.reverse()
    display_values.reverse()

    plt.clf()
    # Height: 2 rows per bar + (N-1) spacers + 6 rows frame overhead
    height = limit * 2 + (limit - 1) + 6
    # Width: base 80 + extra if labels are particularly long
    max_label_len = max((len(ln) for ln in display_labels), default=0)
    width = _BAR_WIDTH + max(0, max_label_len - 28)
    plt.plotsize(width, height)

    plt.bar(display_labels, display_values, orientation="h", color=_BAR_COLOR)
    plt.title(title)

    _show(plt.build())
    return True
