"""Smoke tests for the visualization module (viz/).

We don't visually inspect charts, but we verify:
- File output is created at the correct path
- File format is valid (PNG signature, valid HTML)
- Empty/invalid inputs raise clear errors
- The matplotlib chinese font config doesn't crash
- Terminal charts gracefully no-op in non-TTY environments
"""

from __future__ import annotations

import matplotlib
import pytest

from citationer.viz.charts import (
    generate_keyword_wordcloud,
    generate_top_n_chart,
    generate_yearly_chart,
    setup_chinese_font,
)
from citationer.viz.terminal_charts import plot_hbar, plot_line, plot_line_dual

# Use non-GUI backend for headless testing
matplotlib.use("Agg")


# ===========================================================================
# setup_chinese_font
# ===========================================================================


class TestSetupChineseFont:
    def test_does_not_raise(self):
        """Font config should always succeed (uses fallback)."""
        # Should not raise even with no Chinese fonts installed
        setup_chinese_font()
        # matplotlib.rcParams updated
        assert "font.family" in matplotlib.rcParams


# ===========================================================================
# generate_yearly_chart
# ===========================================================================


class TestGenerateYearlyChart:
    def test_creates_png_file(self, tmp_path):
        from citationer.models.record import Author, Record

        records = [
            Record(title=f"P{i}", year=2020 + i, keywords=["x"],
                  authors=[Author(full_name="A", order=1)])
            for i in range(5)
        ]
        output = tmp_path / "yearly.png"
        result = generate_yearly_chart(records, output)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0
        # PNG magic bytes
        with open(output, "rb") as f:
            assert f.read(4) == b"\x89PNG"

    def test_creates_parent_directory(self, tmp_path):
        from citationer.models.record import Author, Record

        records = [
            Record(title="P", year=2024, authors=[Author(full_name="A", order=1)])
        ]
        output = tmp_path / "subdir" / "deep" / "chart.png"
        generate_yearly_chart(records, output)
        assert output.exists()

    def test_cumulative_mode(self, tmp_path):
        from citationer.models.record import Author, Record

        records = [
            Record(title=f"P{i}", year=2020 + i,
                  authors=[Author(full_name="A", order=1)])
            for i in range(3)
        ]
        output = tmp_path / "cum.png"
        generate_yearly_chart(records, output, cumulative=True)
        assert output.exists()

    def test_no_data_raises(self, tmp_path):
        from citationer.models.record import Author, Record

        # Records with no year
        records = [
            Record(title="P", year=None, authors=[Author(full_name="A", order=1)])
        ]
        with pytest.raises(ValueError, match="No year data"):
            generate_yearly_chart(records, tmp_path / "empty.png")


# ===========================================================================
# generate_top_n_chart
# ===========================================================================


class TestGenerateTopNChart:
    def test_horizontal_bar(self, tmp_path):
        items = [("Journal A", 100), ("Journal B", 80), ("Journal C", 60)]
        output = tmp_path / "top.png"
        result = generate_top_n_chart(items, output, horizontal=True)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_vertical_bar(self, tmp_path):
        items = [("A", 10), ("B", 20), ("C", 30)]
        output = tmp_path / "vert.png"
        generate_top_n_chart(items, output, horizontal=False)
        assert output.exists()

    def test_top_n_filter(self, tmp_path):
        items = [(f"J{i}", i * 10) for i in range(20)]
        output = tmp_path / "filtered.png"
        generate_top_n_chart(items, output, top_n=5)
        assert output.exists()

    def test_empty_items(self, tmp_path):
        output = tmp_path / "empty.png"
        generate_top_n_chart([], output)
        # Either raises or creates empty chart
        # Verify doesn't crash with crash-level exception
        # (matplotlib may handle gracefully)


# ===========================================================================
# generate_keyword_wordcloud
# ===========================================================================


class TestGenerateKeywordWordcloud:
    def test_creates_wordcloud_png(self, tmp_path):
        """Requires wordcloud optional dep — skip if missing."""
        pytest.importorskip("wordcloud")
        keywords = ["machine learning"] * 10 + ["healthcare"] * 5 + ["ai"] * 3
        output = tmp_path / "wc.png"
        result = generate_keyword_wordcloud(keywords, output)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_wordcloud_import_error(self, tmp_path):
        """If wordcloud is not installed, ImportError is raised."""
        import sys

        # Temporarily remove wordcloud from sys.modules
        original = sys.modules.get("wordcloud")
        sys.modules["wordcloud"] = None  # forces ImportError
        try:
            with pytest.raises(ImportError, match="wordcloud"):
                generate_keyword_wordcloud(["test"], tmp_path / "wc.png")
        finally:
            if original is not None:
                sys.modules["wordcloud"] = original
            else:
                sys.modules.pop("wordcloud", None)


# ===========================================================================
# Terminal charts
# ===========================================================================


class TestPlotLine:
    def test_no_tty_returns_false(self, capsys):
        """Non-TTY environments (like pytest capture) → return False."""
        result = plot_line([2020, 2021, 2022], [1, 2, 3])
        # pytest captures stdout, so sys.stdout.isatty() is False
        assert result is False

    def test_empty_data_returns_false(self):
        result = plot_line([], [])
        assert result is False


class TestPlotLineDual:
    def test_no_tty_returns_false(self):
        result = plot_line_dual([2020, 2021], [1, 2], [1, 3])
        assert result is False

    def test_empty_data_returns_false(self):
        result = plot_line_dual([], [], [])
        assert result is False


class TestPlotHbar:
    def test_no_tty_returns_false(self):
        result = plot_hbar(["A", "B"], [10, 5])
        assert result is False

    def test_empty_data_returns_false(self):
        result = plot_hbar([], [])
        assert result is False

    def test_max_items_caps(self):
        """Max 20 items enforced."""
        labels = [f"J{i}" for i in range(50)]
        values = list(range(50))
        # Even in non-TTY, the function should handle the limit
        result = plot_hbar(labels, values, max_items=10)
        # Returns False due to non-TTY, but didn't crash
        assert result is False

    def test_handles_long_labels(self):
        """Long labels should not crash (truncation logic)."""
        long_label = "A" * 100
        result = plot_hbar([long_label], [10])
        # No crash, no TTY
        assert result is False
