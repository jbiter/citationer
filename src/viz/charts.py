"""Chart generation using matplotlib.

Generates static PNG/SVG charts for annual trends, top-N rankings,
and other descriptive statistics.
"""

from __future__ import annotations

from pathlib import Path

from citationer.analysis.stats import StatsEngine


def setup_chinese_font() -> None:
    """Try to configure matplotlib for Chinese font support."""
    import matplotlib
    import matplotlib.font_manager as fm

    # Common Chinese fonts on macOS, Linux, and Windows
    candidate_fonts = [
        "PingFang SC",
        "Heiti SC",
        "STHeiti",
        "Arial Unicode MS",
        "SimHei",
        "Microsoft YaHei",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
        "Noto Sans CJK SC",
        "Noto Sans SC",
    ]

    available_fonts = {f.name for f in fm.fontManager.ttflist}
    for font_name in candidate_fonts:
        if font_name in available_fonts:
            matplotlib.rcParams["font.family"] = font_name
            return

    # Fallback: try sans-serif with fallback
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = candidate_fonts


def generate_yearly_chart(
    records,
    output_path: Path,
    title: str = "Annual Publication Trend",
    cumulative: bool = False,
) -> Path:
    """Generate a publication trend line chart."""
    import matplotlib.pyplot as plt

    setup_chinese_font()

    engine = StatsEngine(records)
    stats = engine.yearly()

    if not stats.year_counts:
        raise ValueError("No year data available")

    years = sorted(stats.year_counts)
    counts = [stats.year_counts[y] for y in years]

    fig, ax1 = plt.subplots(figsize=(10, 5))

    # Bar chart for yearly counts
    ax1.bar(years, counts, color="steelblue", alpha=0.7, label="Publications")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Publications", color="steelblue")
    ax1.tick_params(axis="y", labelcolor="steelblue")

    # Trend line
    if len(years) > 1:
        z = [x - years[0] for x in years]
        # Simple linear fit
        n = len(years)
        x_mean = sum(z) / n
        y_mean = sum(counts) / n
        slope = (
            sum((z[i] - x_mean) * (counts[i] - y_mean) for i in range(n))
            / sum((x - x_mean) ** 2 for x in z)
        )
        intercept = y_mean - slope * x_mean
        trend_y = [slope * x + intercept for x in z]
        ax1.plot(years, trend_y, color="red", linestyle="--", linewidth=1.5, label="Trend")

    ax1.set_xticks(years)
    ax1.set_xticklabels(years, rotation=45)

    # Cumulative overlay
    if cumulative:
        ax2 = ax1.twinx()
        cum_values = [stats.cumulative[y] for y in years]
        ax2.plot(years, cum_values, color="darkorange", linewidth=2, marker="o", label="Cumulative")
        ax2.set_ylabel("Cumulative", color="darkorange")
        ax2.tick_params(axis="y", labelcolor="darkorange")

    fig.suptitle(title)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return output_path


def generate_top_n_chart(
    items: list[tuple[str, int]],
    output_path: Path,
    title: str = "Top Items",
    xlabel: str = "Count",
    horizontal: bool = True,
    top_n: int | None = None,
) -> Path:
    """Generate a horizontal bar chart for Top-N rankings."""
    import matplotlib.pyplot as plt

    setup_chinese_font()

    if top_n:
        items = items[:top_n]

    # Reverse for horizontal bar (bottom to top)
    if horizontal:
        items = list(reversed(items))

    names = [item[0] for item in items]
    values = [item[1] for item in items]

    fig, ax = plt.subplots(figsize=(10, max(6, len(items) * 0.4)))

    if horizontal:
        colors = plt.cm.Blues([0.3 + 0.7 * i / max(1, len(values) - 1) for i in range(len(values))])
        ax.barh(range(len(names)), values, color=colors)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.set_xlabel(xlabel)
    else:
        ax.bar(names, values, color="steelblue", alpha=0.7)
        ax.set_xticklabels(names, rotation=45, ha="right")
        ax.set_ylabel(xlabel)

    ax.set_title(title)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return output_path


def generate_keyword_wordcloud(
    keywords: list[str],
    output_path: Path,
    width: int = 800,
    height: int = 600,
) -> Path:
    """Generate a word cloud for keywords.

    Requires the 'wordcloud' library (optional dependency).
    """
    try:
        from wordcloud import WordCloud
    except ImportError as e:
        raise ImportError(
            "wordcloud library is required for word cloud generation. "
            "Install with: pip install wordcloud"
        ) from e

    # Count keyword frequencies
    from collections import Counter
    freq = Counter(keywords)

    setup_chinese_font()

    wc = WordCloud(
        width=width,
        height=height,
        background_color="white",
        max_words=200,
        relative_scaling=0.5,
        colormap="Blues",
    )
    wc.generate_from_frequencies(freq)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wc.to_file(str(output_path))

    return output_path
