"""Analysis engines for stats, network, text, and trend."""

from citationer.analysis.dedup import DedupEngine
from citationer.analysis.network import NetworkEngine
from citationer.analysis.stats import StatsEngine
from citationer.analysis.text import TextEngine

__all__ = ["DedupEngine", "NetworkEngine", "StatsEngine", "TextEngine"]
