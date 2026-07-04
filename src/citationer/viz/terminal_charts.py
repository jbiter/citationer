"""Terminal-native chart rendering via plotext.

Provides two core functions for stats command visualisation:

- :func:`plot_line` — braille line chart for yearly trends
- :func:`plot_hbar` — horizontal bar chart for rankings

Both detect non-TTY output (pipes / redirects) and return ``None`` so
callers can fall back to Rich tables.
"""

from __future__ import annotations

import sys


def _is_tty() -> bool:
    """Return True if stdout is a real terminal (not piped or redirected)."""
    return sys.stdout.isatty()


def plot_line(
    years: list[int],
    counts: list[int],
    *,
    title: str = "Publication Trend",
    xlabel: str = "Year",
    ylabel: str = "Publications",
) -> str | None:
    """Render a braille line chart of yearly publication counts.

    Returns the ANSI string, or ``None`` if stdout is not a TTY.
    """
    if not _is_tty() or not years:
        return None

    try:
        import plotext as plt  # noqa: F811
    except ImportError:
        return None

    plt.clf()
    plt.plot(years, counts, marker="braille", color="cyan")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True)
    return plt.build()


def plot_line_dual(
    years: list[int],
    counts: list[int],
    cumulative: list[int],
    *,
    title: str = "Publication Trend (with Cumulative)",
) -> str | None:
    """Line chart with bars for annual counts + line for cumulative.

    Returns the ANSI string, or ``None`` if stdout is not a TTY.
    """
    if not _is_tty() or not years:
        return None

    try:
        import plotext as plt  # noqa: F811
    except ImportError:
        return None

    plt.clf()

    # Bar-plot for annual counts (left axis)
    plt.bar(years, counts, color="blue", label="Annual")
    plt.xlabel("Year")
    plt.ylabel("Publications", color="blue")
    plt.tick_params(axis="y", color="blue")

    # Line-plot for cumulative (right axis, twin)
    plt.twinx()
    plt.plot(years, cumulative, marker="braille", color="gold", label="Cumulative")
    plt.ylabel("Cumulative", color="gold")
    plt.tick_params(axis="y", color="gold")

    plt.title(title)
    plt.grid(True)
    return plt.build()


def plot_hbar(
    labels: list[str],
    values: list[int],
    *,
    title: str = "Ranking",
    max_items: int = 20,
) -> str | None:
    """Render a horizontal bar chart for Top-N rankings.

    Labels longer than 24 characters are truncated.

    Returns the ANSI string, or ``None`` if stdout is not a TTY.
    """
    if not _is_tty() or not labels:
        return None

    try:
        import plotext as plt  # noqa: F811
    except ImportError:
        return None

    # Truncate long labels
    short_labels = [
        (lbl[:22] + "…") if len(lbl) > 24 else lbl for lbl in labels[:max_items]
    ]
    short_values = values[:max_items]

    # Reverse so the largest bar is at the top (plotext plots bottom-up)
    short_labels.reverse()
    short_values.reverse()

    plt.clf()
    plt.bar(short_labels, short_values, orientation="h", color="blue")
    plt.title(title)
    return plt.build()
