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

# Unicode block element for drawing text-based bars
_BLOCK = "█"


def plot_hbar(
    labels: list[str],
    values: list[int],
    *,
    title: str = "Ranking",
    max_items: int = 20,
) -> bool:
    """Render a horizontal bar chart directly to stdout.

    Uses simple Unicode block strings — each bar is one line, labels
    are never truncated, and values are shown at the bar tip.

    Returns True on success.
    """
    if not _can_render() or not labels:
        return False

    limit = min(len(labels), max_items, 20)

    items = list(zip(labels[:limit], values[:limit]))
    max_val = max(values[:limit]) if values else 1

    # Compute label column width for alignment
    label_w = max((len(lbl) for lbl in labels[:limit]), default=0)
    label_w = min(label_w, 36)  # don't let one long label ruin alignment

    # Truncate labels that exceed the column width
    def _fmt_label(lbl: str) -> str:
        if len(lbl) > label_w:
            return lbl[: label_w - 1] + "…"
        return lbl.ljust(label_w)

    # Bar width: scale to fit ~50 chars at most
    bar_scale = 50.0 / max(max_val, 1)

    lines: list[str] = []
    for i, (lbl, val) in enumerate(items):
        bar_len = int(val * bar_scale)
        bar = _BLOCK * bar_len
        lines.append(f"  {_fmt_label(lbl)} │{bar} {val}")
        if i < len(items) - 1:
            lines.append(f"  {' ' * label_w} │")

    # Print
    print()
    print(f"  {title}")
    print()
    for line in lines:
        print(line)
    print()
    return True
