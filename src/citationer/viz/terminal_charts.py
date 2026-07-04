"""Terminal-native chart rendering via plotext.

Provides chart functions for stats command visualisation.
Each function renders directly to stdout via plotext.show() and
returns True on success, False if the chart could not be rendered
(e.g. non-TTY output, missing plotext, or empty data).
"""

from __future__ import annotations

import sys


def _can_render() -> bool:
    """Return True if stdout is a real terminal and plotext is available."""
    if not sys.stdout.isatty():
        return False
    try:
        import plotext  # noqa: F401
        return True
    except ImportError:
        return False


def plot_line(
    years: list[int],
    counts: list[int],
    *,
    title: str = "Publication Trend",
    xlabel: str = "Year",
    ylabel: str = "Publications",
) -> bool:
    """Render a braille line chart of yearly publication counts.

    Returns True on success, False if rendering is not possible.
    """
    if not _can_render() or not years:
        return False

    import plotext as plt  # noqa: F811

    plt.clf()
    plt.plot(years, counts, marker="braille", color="cyan")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.show()
    return True


def plot_line_dual(
    years: list[int],
    counts: list[int],
    cumulative: list[int],
    *,
    title: str = "Publication Trend (with Cumulative)",
) -> bool:
    """Dual chart: bars for annual counts + braille line for cumulative.

    Returns True on success, False if rendering is not possible.
    """
    if not _can_render() or not years:
        return False

    import plotext as plt  # noqa: F811

    plt.clf()

    plt.bar(years, counts, color="blue", label="Annual")
    plt.xlabel("Year")
    plt.ylabel("Publications", color="blue")
    plt.tick_params(axis="y", color="blue")

    plt.twinx()
    plt.plot(years, cumulative, marker="braille", color="gold", label="Cumulative")
    plt.ylabel("Cumulative", color="gold")
    plt.tick_params(axis="y", color="gold")

    plt.title(title)
    plt.grid(True)
    plt.show()
    return True


def plot_hbar(
    labels: list[str],
    values: list[int],
    *,
    title: str = "Ranking",
    max_items: int = 20,
) -> bool:
    """Render a horizontal bar chart for Top-N rankings.

    Labels longer than 24 characters are truncated.
    Returns True on success, False if rendering is not possible.
    """
    if not _can_render() or not labels:
        return False

    import plotext as plt  # noqa: F811

    short_labels = [
        (lbl[:22] + "…") if len(lbl) > 24 else lbl for lbl in labels[:max_items]
    ]
    short_values = values[:max_items]
    short_labels.reverse()
    short_values.reverse()

    plt.clf()
    plt.bar(short_labels, short_values, orientation="h", color="blue")
    plt.title(title)
    plt.show()
    return True
