"""Tests for citationer pdf commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citationer.cli.main import app


@pytest.fixture(autouse=True)
def _skip_pypdf_check(monkeypatch):
    """Bypass the pypdf availability check so tests run without the optional dep."""
    monkeypatch.setattr("citationer.cli.pdf_cmd._ensure_pypdf", lambda: None)


class TestPdfExtractCommand:
    def test_pdf_extract_help(self, cli_runner):
        result = cli_runner.invoke(app, ["pdf", "--help"])
        assert result.exit_code == 0
        assert "extract" in result.output

    def test_pdf_extract_success(self, cli_runner, clean_cwd, monkeypatch, tmp_path):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "paper.pdf").write_bytes(b"fake")

        def _fake_reader(_p):
            class Page:
                def extract_text(self) -> str:
                    return "Sample PDF content"

            class Reader:
                pages = [Page()]

            return Reader()

        monkeypatch.setattr("pypdf.PdfReader", _fake_reader)
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            app, ["pdf", "extract", str(pdf_dir), "-o", "out.json"]
        )

        assert result.exit_code == 0, result.output
        assert "处理完成" in result.output
        assert Path("out.json").exists()

        data = json.loads(Path("out.json").read_text(encoding="utf-8"))
        assert data["summary"]["success"] == 1
        assert data["files"][0]["filename"] == "paper.pdf"
        assert "Sample PDF content" in data["files"][0]["text"]

    def test_pdf_extract_empty_dir(self, cli_runner, clean_cwd, monkeypatch, tmp_path):
        pdf_dir = tmp_path / "empty"
        pdf_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            app, ["pdf", "extract", str(pdf_dir), "-o", "empty.json"]
        )

        assert result.exit_code == 0, result.output
        assert Path("empty.json").exists()
        data = json.loads(Path("empty.json").read_text(encoding="utf-8"))
        assert data["summary"]["total"] == 0

    def test_pdf_extract_error_file(self, cli_runner, clean_cwd, monkeypatch, tmp_path):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "broken.pdf").write_bytes(b"fake")

        def _raise(_p):
            raise RuntimeError("boom")

        monkeypatch.setattr("pypdf.PdfReader", _raise)
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            app, ["pdf", "extract", str(pdf_dir), "-o", "err.json"]
        )

        assert result.exit_code == 0, result.output
        data = json.loads(Path("err.json").read_text(encoding="utf-8"))
        assert data["summary"]["total"] == 1
        assert data["summary"]["failed"] == 1
        assert data["errors"][0]["status"] == "error"


class TestPdfTopicsCommand:
    @staticmethod
    def _fake_reader(text: str):
        def _reader(_p):
            class Page:
                def extract_text(self) -> str:
                    return text

            class Reader:
                pages = [Page()]

            return Reader()

        return _reader

    @staticmethod
    def _fake_engine_class(monkeypatch, topics=None):
        from citationer.analysis.text import TopicModelResult

        result = TopicModelResult(
            method="lda",
            num_topics=len(topics or []),
            topics=topics or [],
            coherence_score=0.42,
        )

        class FakeEngine:
            def __init__(self, records):
                self.records = records

            def topics(self, **kwargs):
                return result

        monkeypatch.setattr("citationer.cli.pdf_cmd.TextEngine", FakeEngine)

    def test_pdf_topics_help(self, cli_runner):
        result = cli_runner.invoke(app, ["pdf", "topics", "--help"])
        assert result.exit_code == 0
        assert "num-topics" in result.output
        assert "method" in result.output

    def test_pdf_topics_success(self, cli_runner, clean_cwd, monkeypatch, tmp_path):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "paper1.pdf").write_bytes(b"fake")
        (pdf_dir / "paper2.pdf").write_bytes(b"fake")

        monkeypatch.setattr(
            "pypdf.PdfReader", self._fake_reader("machine learning model training")
        )
        self._fake_engine_class(
            monkeypatch,
            topics=[[("learning", 0.5), ("model", 0.3)], [("network", 0.4)]],
        )
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            app, ["pdf", "topics", str(pdf_dir), "--num-topics", "2", "-o", "t.json"]
        )

        assert result.exit_code == 0, result.output
        assert "发现 2 个主题" in result.output
        assert "learning" in result.output
        assert "一致性分数: 0.420" in result.output

        data = json.loads(Path("t.json").read_text(encoding="utf-8"))
        assert data["num_topics"] == 2
        assert data["method"] == "lda"
        assert data["documents"] == 2
        assert data["topics"][0][0] == {"term": "learning", "weight": 0.5}

    def test_pdf_topics_skips_empty_and_failed(
        self, cli_runner, clean_cwd, monkeypatch, tmp_path
    ):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "good.pdf").write_bytes(b"fake")
        (pdf_dir / "empty.pdf").write_bytes(b"fake")

        def _reader(p: str):
            path = Path(p)
            if path.name == "empty.pdf":
                return type("R", (), {"pages": []})()
            return TestPdfTopicsCommand._fake_reader("real content")(p)

        monkeypatch.setattr("pypdf.PdfReader", _reader)
        self._fake_engine_class(monkeypatch, topics=[[("topic", 0.9)]])
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(app, ["pdf", "topics", str(pdf_dir)])

        assert result.exit_code == 0, result.output
        assert "1 个文件文本为空" in result.output
        assert "发现 1 个主题" in result.output

    def test_pdf_topics_no_texts(self, cli_runner, clean_cwd, monkeypatch, tmp_path):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "blank.pdf").write_bytes(b"fake")

        monkeypatch.setattr(
            "pypdf.PdfReader", self._fake_reader("")
        )
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(app, ["pdf", "topics", str(pdf_dir)])

        assert result.exit_code == 1
        assert "没有可分析的 PDF 文本" in result.output

    def test_pdf_topics_empty_result(
        self, cli_runner, clean_cwd, monkeypatch, tmp_path
    ):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "paper.pdf").write_bytes(b"fake")

        monkeypatch.setattr(
            "pypdf.PdfReader", self._fake_reader("some text content")
        )
        self._fake_engine_class(monkeypatch, topics=[])
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(app, ["pdf", "topics", str(pdf_dir)])

        assert result.exit_code == 1
        assert "未能发现主题" in result.output
