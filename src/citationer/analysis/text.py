"""Text mining and NLP engine for bibliographic records.

Provides language detection, preprocessing (tokenization + stop word removal),
keyword frequency analysis, topic modeling (LDA/NMF), extractive summarization,
and document clustering.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from citationer.models.record import Record

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def detect_language(text: str) -> str:
    """Detect if text is predominantly Chinese or English using CJK character ratio.

    Returns "zh" if > 10% of characters are in the CJK Unified Ideographs range,
    otherwise "en".
    """
    if not text:
        return "en"
    cjk_count = sum(1 for c in text if "一" <= c <= "鿿")
    return "zh" if cjk_count / max(len(text), 1) > 0.1 else "en"


# ---------------------------------------------------------------------------
# Stop words
# ---------------------------------------------------------------------------

def _load_stopwords(filename: str) -> set[str]:
    """Load stop words from a bundled data file."""
    data_dir = Path(__file__).parent.parent / "data"
    path = data_dir / filename
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip() and not line.startswith("#")}


_STOPWORDS_ZH: set[str] | None = None
_STOPWORDS_EN: set[str] | None = None
_SPACY_NLP: Any = None  # cached spaCy model

# Minimal built-in stop words — used as fallback if the bundled data files
# cannot be loaded (e.g. when package data is not installed).
_FALLBACK_STOPWORDS_EN: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "i", "me", "my",
    "we", "our", "you", "your", "he", "him", "his", "she", "her", "it",
    "its", "they", "them", "their", "this", "that", "these", "those",
    "in", "on", "at", "to", "for", "of", "with", "from", "by", "as",
    "or", "and", "but", "not", "no", "nor", "so", "if", "then", "than",
    "too", "very", "just", "about", "also", "into", "over", "such",
    "only", "other", "new", "some", "any", "each", "all", "both", "few",
    "more", "most", "one", "two", "first", "last", "up", "out", "now",
    "when", "where", "how", "what", "which", "who",
    "paper", "study", "research", "based", "using", "used", "results",
    "method", "methods", "approach", "analysis", "data", "model",
}
_FALLBACK_STOPWORDS_ZH: set[str] = {
    "的", "了", "在", "是", "和", "也", "就", "都", "不", "与", "及",
    "或", "但", "而", "且", "虽", "然", "如", "果", "因", "为", "所",
    "以", "能", "够", "可", "会", "将", "把", "被", "对", "从", "由",
    "向", "到", "于", "之", "其", "这", "那", "等", "等", "等",
}


def _get_stopwords_zh() -> set[str]:
    global _STOPWORDS_ZH
    if _STOPWORDS_ZH is None:
        loaded = _load_stopwords("stopwords_zh.txt")
        _STOPWORDS_ZH = loaded if loaded else _FALLBACK_STOPWORDS_ZH
    return _STOPWORDS_ZH


def _get_stopwords_en() -> set[str]:
    global _STOPWORDS_EN
    if _STOPWORDS_EN is None:
        loaded = _load_stopwords("stopwords_en.txt")
        _STOPWORDS_EN = loaded if loaded else _FALLBACK_STOPWORDS_EN
    return _STOPWORDS_EN


def _extract_text(record: Record, field: str = "all") -> str:
    """Extract text from a record based on the specified field."""
    parts: list[str] = []
    if field in ("title", "all"):
        parts.append(record.title or "")
    if field in ("abstract", "all"):
        if record.abstract:
            parts.append(record.abstract)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PreprocessResult:
    """Result of preprocessing a single record."""

    title: str
    language: str
    tokens: list[str]
    token_count: int
    original_length: int


@dataclass
class KeywordStats:
    """Keyword frequency analysis results."""

    top_keywords: list[tuple[str, int]] = field(default_factory=list)
    total_unique: int = 0
    # keyword → {year: count} for heatmap data
    yearly_distribution: dict[str, dict[int, int]] = field(default_factory=dict)


@dataclass
class TopicModelResult:
    """Topic modeling results."""

    method: str = "lda"
    num_topics: int = 0
    topics: list[list[tuple[str, float]]] = field(default_factory=list)
    coherence_score: float | None = None
    perplexity: float | None = None


@dataclass
class SummarizeResult:
    """Extractive summarization results."""

    sentences: list[tuple[str, float]] = field(default_factory=list)


@dataclass
class ClusterResult:
    """Document clustering results."""

    method: str = "kmeans"
    n_clusters: int = 0
    labels: list[int] = field(default_factory=list)
    cluster_sizes: dict[int, int] = field(default_factory=dict)
    cluster_terms: dict[int, list[str]] = field(default_factory=dict)
    silhouette_score: float | None = None


# ---------------------------------------------------------------------------
# TextEngine
# ---------------------------------------------------------------------------


class TextEngine:
    """NLP and text mining engine for bibliographic record collections."""

    def __init__(self, records: list[Record]) -> None:
        self._records = records

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def preprocess(
        self,
        field: str = "all",
        lang: str = "auto",
    ) -> list[PreprocessResult]:
        """Tokenize and clean text for each record.

        Args:
            field: Which fields to process ("title", "abstract", "all").
            lang: Language hint ("zh", "en", or "auto" for auto-detection).
        """
        results: list[PreprocessResult] = []

        for r in self._records:
            text = _extract_text(r, field)
            if not text:
                results.append(
                    PreprocessResult(
                        title=r.title or "(no title)",
                        language="unknown",
                        tokens=[],
                        token_count=0,
                        original_length=0,
                    )
                )
                continue

            # Determine language
            detected = r.language or detect_language(text)
            if lang != "auto":
                detected = lang

            # Tokenize
            if detected == "zh":
                tokens = self._tokenize_zh(text)
            else:
                tokens = self._tokenize_en(text)

            results.append(
                PreprocessResult(
                    title=r.title or "(no title)",
                    language=detected,
                    tokens=tokens,
                    token_count=len(tokens),
                    original_length=len(text),
                )
            )

        return results

    def _tokenize_zh(self, text: str) -> list[str]:
        """Tokenize Chinese text using jieba."""
        try:
            import jieba
        except ImportError:
            # Fallback: character-level tokenization
            return [c for c in text if "一" <= c <= "鿿"]

        stopwords = _get_stopwords_zh()
        tokens = jieba.cut(text)
        return [
            t.strip() for t in tokens
            if t.strip() and t.strip() not in stopwords and len(t.strip()) > 1
        ]

    def _tokenize_en(self, text: str) -> list[str]:
        """Tokenize English text using simple regex (spaCy as optional upgrade)."""
        global _SPACY_NLP
        try:
            import spacy
            if _SPACY_NLP is None:
                try:
                    _SPACY_NLP = spacy.load("en_core_web_sm")
                except OSError:
                    return self._tokenize_en_simple(text)

            stopwords = _get_stopwords_en()
            doc = _SPACY_NLP(text)
            tokens: list[str] = []
            for token in doc:
                if token.is_alpha and not token.is_stop:
                    lemma = token.lemma_.lower().strip()
                    if lemma and lemma not in stopwords and len(lemma) > 1:
                        tokens.append(lemma)
            return tokens
        except ImportError:
            return self._tokenize_en_simple(text)

    @staticmethod
    def _tokenize_en_simple(text: str) -> list[str]:
        """Simple English tokenizer (regex-based, no external deps)."""
        stopwords = _get_stopwords_en()
        # Extract word tokens
        words = re.findall(r"[a-zA-Z]{2,}", text.lower())
        return [w for w in words if w not in stopwords]

    # ------------------------------------------------------------------
    # Keywords
    # ------------------------------------------------------------------

    def keywords(
        self,
        top_n: int = 50,
        per_year: bool = False,
        min_count: int = 1,
    ) -> KeywordStats:
        """Compute keyword frequency statistics.

        Args:
            top_n: Number of top keywords to return.
            per_year: If True, also compute keyword × year distribution.
            min_count: Minimum occurrence count for a keyword to be included.
        """
        counter: Counter[str] = Counter()
        yearly: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

        for r in self._records:
            year = r.year
            all_kw = list(r.keywords)
            if r.keywords_en:
                all_kw.extend(r.keywords_en)

            for kw in all_kw:
                kw_clean = kw.strip()
                if kw_clean and len(kw_clean) >= 2:
                    counter[kw_clean] += 1
                    if per_year and year is not None:
                        yearly[kw_clean][year] += 1

        # Filter by min_count
        filtered = [(kw, c) for kw, c in counter.items() if c >= min_count]
        top = sorted(filtered, key=lambda x: -x[1])[:top_n]

        return KeywordStats(
            top_keywords=top,
            total_unique=len(counter),
            yearly_distribution=dict(yearly) if per_year else {},
        )

    # ------------------------------------------------------------------
    # Topic modeling
    # ------------------------------------------------------------------

    def topics(
        self,
        num_topics: int | None = None,
        max_terms: int = 10,
        method: str = "lda",
        max_features: int = 5000,
    ) -> TopicModelResult:
        """Perform topic modeling on record abstracts and titles.

        Args:
            num_topics: Number of topics (auto-detected if None, max 15).
            max_terms: Number of top terms to show per topic.
            method: "lda" (gensim) or "nmf" (sklearn).
            max_features: Max TF-IDF features for vectorization.
        """
        # Build corpus from preprocessed tokens
        preprocessed = self.preprocess(field="all")
        texts = [p.tokens for p in preprocessed if p.tokens]
        if not texts:
            return TopicModelResult(method=method)

        if method == "nmf":
            return self._topics_nmf(texts, num_topics, max_terms, max_features)
        else:
            return self._topics_lda(texts, num_topics, max_terms)

    def _topics_lda(
        self,
        texts: list[list[str]],
        num_topics: int | None,
        max_terms: int,
    ) -> TopicModelResult:
        """LDA topic modeling via gensim."""
        try:
            import gensim
            from gensim import corpora
        except ImportError:
            return TopicModelResult(method="lda", num_topics=0)

        # Build dictionary and corpus
        dictionary = corpora.Dictionary(texts)
        dictionary.filter_extremes(no_below=2, no_above=0.9)
        corpus = [dictionary.doc2bow(text) for text in texts]

        if not dictionary or not corpus:
            return TopicModelResult(method="lda", num_topics=0)

        # Auto-detect number of topics if not specified
        if num_topics is None:
            num_topics = min(len(dictionary) // 10, 15)
            num_topics = max(num_topics, 2)

        try:
            model = gensim.models.LdaModel(
                corpus=corpus,
                id2word=dictionary,
                num_topics=num_topics,
                passes=10,
                random_state=42,
                chunksize=max(1, len(corpus) // 10),
            )
        except (ValueError, RuntimeError):
            return TopicModelResult(method="lda", num_topics=0)

        # Extract topics
        topics_out: list[list[tuple[str, float]]] = []
        for topic_id in range(num_topics):
            terms = model.show_topic(topic_id, topn=max_terms)
            if terms:
                topics_out.append(terms)

        # Compute coherence if possible
        coherence: float | None = None
        try:
            from gensim.models import CoherenceModel
            cm = CoherenceModel(
                model=model, texts=texts, dictionary=dictionary, coherence="c_v",
            )
            coherence = cm.get_coherence()
        except (ValueError, ImportError):
            pass

        return TopicModelResult(
            method="lda",
            num_topics=len(topics_out),
            topics=topics_out,
            coherence_score=coherence,
        )

    def _topics_nmf(
        self,
        texts: list[list[str]],
        num_topics: int | None,
        max_terms: int,
        max_features: int,
    ) -> TopicModelResult:
        """NMF topic modeling via sklearn."""
        try:
            from sklearn.decomposition import NMF
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            return TopicModelResult(method="nmf", num_topics=0)

        # Join tokens back to strings for TF-IDF
        documents = [" ".join(tokens) for tokens in texts]
        if not documents:
            return TopicModelResult(method="nmf", num_topics=0)

        vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words="english",
            max_df=0.9,
            min_df=2,
        )
        tfidf = vectorizer.fit_transform(documents)

        if num_topics is None:
            num_topics = min(tfidf.shape[1] // 10, 15)
            num_topics = max(num_topics, 2)

        feature_names = vectorizer.get_feature_names_out()

        try:
            model = NMF(
                n_components=num_topics,
                random_state=42,
                max_iter=500,
            )
            model.fit(tfidf)
        except (ValueError, RuntimeError):
            return TopicModelResult(method="nmf", num_topics=0)

        topics_out: list[list[tuple[str, float]]] = []
        for topic_idx, topic in enumerate(model.components_):
            top_indices = topic.argsort()[:-(max_terms + 1):-1]
            top_terms = [(feature_names[i], float(topic[i])) for i in top_indices]
            topics_out.append(top_terms)

        return TopicModelResult(
            method="nmf",
            num_topics=len(topics_out),
            topics=topics_out,
        )

    # ------------------------------------------------------------------
    # Extractive summarization
    # ------------------------------------------------------------------

    def summarize(self, max_sentences: int = 10) -> SummarizeResult:
        """Extractive summarization using TF-IDF sentence scoring.

        Args:
            max_sentences: Maximum number of sentences to extract.
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            return SummarizeResult()

        # Collect sentences; cap at 5000 to keep TF-IDF matrix manageable.
        # For large datasets the first pass collects titles only (which are
        # shorter and more informative), falling back to abstracts only if
        # needed.
        max_input = 5000
        all_sentences: list[str] = []

        # First pass: titles (most informative, fewer sentences)
        for r in self._records:
            if r.title:
                sents = re.split(r"[.。！!？?\n]+", str(r.title))
                all_sentences.extend(s.strip() for s in sents if len(s.strip()) > 10)
                if len(all_sentences) >= max_input:
                    break

        # Second pass: abstracts (only if we have room)
        if len(all_sentences) < max_input:
            for r in self._records:
                if r.abstract:
                    sents = re.split(r"[.。！!？?\n]+", str(r.abstract))
                    all_sentences.extend(s.strip() for s in sents if len(s.strip()) > 10)
                    if len(all_sentences) >= max_input:
                        break

        if not all_sentences:
            return SummarizeResult()

        # Cap total input
        all_sentences = all_sentences[:max_input]

        # TF-IDF vectorize
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(all_sentences)

        # Score each sentence by sum of TF-IDF weights
        scores = tfidf_matrix.sum(axis=1).A1  # dense array from sparse sums

        # Select top sentences
        ranked = sorted(
            zip(all_sentences, scores), key=lambda x: -x[1]
        )[:max_sentences]

        return SummarizeResult(sentences=ranked)

    # ------------------------------------------------------------------
    # Clustering
    # ------------------------------------------------------------------

    def cluster(
        self,
        method: str = "kmeans",
        n_clusters: int | None = None,
        vectorizer: str = "tfidf",
    ) -> ClusterResult:
        """Cluster records based on title + abstract similarity.

        Args:
            method: "kmeans" or "hierarchical".
            n_clusters: Number of clusters (auto-detected if None).
            vectorizer: "tfidf" or "sbert" (lazy, requires sentence-transformers).
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            return ClusterResult()

        # Build document texts
        docs: list[str] = []
        for r in self._records:
            parts = [r.title]
            if r.abstract:
                parts.append(r.abstract)
            docs.append(" ".join(p.strip() for p in parts if p))

        if not docs:
            return ClusterResult()

        # Vectorize
        if vectorizer == "sbert":
            vectors = self._vectorize_sbert(docs)
        else:
            tfidf_vec = TfidfVectorizer(max_features=2000, stop_words="english")
            vectors = tfidf_vec.fit_transform(docs)

        # Determine number of clusters
        if n_clusters is None:
            n_clusters = min(max(3, len(docs) // 10), 8)

        # Cap: cannot have more clusters than documents
        if n_clusters > len(docs):
            n_clusters = max(1, len(docs))

        # Cluster
        if method == "hierarchical":
            labels = self._cluster_hierarchical(vectors, n_clusters)
        else:
            labels = self._cluster_kmeans(vectors, n_clusters)

        # Compute cluster stats
        cluster_sizes = dict(Counter(labels))
        cluster_terms = self._extract_cluster_terms(docs, labels)

        # Silhouette score
        silhouette: float | None = None
        try:
            from sklearn.metrics import silhouette_score
            silhouette = float(silhouette_score(vectors, labels))
        except Exception:
            pass

        return ClusterResult(
            method=method,
            n_clusters=n_clusters,
            labels=labels,
            cluster_sizes=cluster_sizes,
            cluster_terms=cluster_terms,
            silhouette_score=silhouette,
        )

    @staticmethod
    def _vectorize_sbert(docs: list[str]):
        """Vectorize using Sentence-BERT (optional)."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for SBERT vectorization. "
                "Install with: pip install sentence-transformers"
            )
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return model.encode(docs)

    @staticmethod
    def _cluster_kmeans(vectors, n_clusters: int) -> list[int]:
        """K-Means clustering."""
        from sklearn.cluster import KMeans
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        return list(model.fit_predict(vectors))

    @staticmethod
    def _cluster_hierarchical(vectors, n_clusters: int) -> list[int]:
        """Agglomerative hierarchical clustering."""
        from sklearn.cluster import AgglomerativeClustering
        model = AgglomerativeClustering(n_clusters=n_clusters)
        if hasattr(vectors, "toarray"):
            return list(model.fit_predict(vectors.toarray()))
        return list(model.fit_predict(vectors))

    @staticmethod
    def _extract_cluster_terms(
        docs: list[str],
        labels: list[int],
        top_n: int = 5,
    ) -> dict[int, list[str]]:
        """Extract representative terms for each cluster."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        cluster_docs: dict[int, list[str]] = defaultdict(list)
        for doc, label in zip(docs, labels):
            cluster_docs[label].append(doc)

        result: dict[int, list[str]] = {}
        for cid, c_docs in cluster_docs.items():
            valid_docs = [d for d in c_docs if d and d.strip()]
            if not valid_docs:
                result[cid] = []
                continue
            vec = TfidfVectorizer(max_features=20, stop_words="english")
            try:
                vec.fit_transform(valid_docs)
                result[cid] = list(vec.get_feature_names_out())[:top_n]
            except ValueError:
                result[cid] = []

        return result
