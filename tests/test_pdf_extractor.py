"""Tests for citationer.pdf.extractor.PdfExtractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from citationer.pdf.extractor import PdfExtractor


class FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class FakeReader:
    def __init__(self, pages: list[FakePage]) -> None:
        self.pages = pages


def _make_fake_reader(texts: list[str]):
    return FakeReader([FakePage(t) for t in texts])


class TestPdfExtractor:
    def test_extract_file_success(self, tmp_path: Path, monkeypatch):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        monkeypatch.setattr(
            "pypdf.PdfReader",
            lambda _p: _make_fake_reader(["Hello world", "Second page"]),
        )

        extractor = PdfExtractor()
        result = extractor.extract_file(pdf_path)

        assert result["status"] == "success"
        assert result["filename"] == "test.pdf"
        assert result["page_count"] == 2
        assert "Hello world" in result["text"]
        assert "Second page" in result["text"]
        assert result["word_count"] == 4

    def test_extract_file_error(self, tmp_path: Path, monkeypatch):
        pdf_path = tmp_path / "broken.pdf"
        pdf_path.write_bytes(b"fake")

        def _raise(_p):
            raise RuntimeError("corrupted file")

        monkeypatch.setattr("pypdf.PdfReader", _raise)

        extractor = PdfExtractor()
        result = extractor.extract_file(pdf_path)

        assert result["status"] == "error"
        assert "corrupted file" in result["error"]

    def test_extract_directory_recursive(self, tmp_path: Path, monkeypatch):
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "1.pdf").write_bytes(b"fake")
        (tmp_path / "b" / "2.pdf").write_bytes(b"fake")

        def _fake_reader(p: str):
            path = Path(p)
            if path.name == "1.pdf":
                return _make_fake_reader(["page one"])
            return _make_fake_reader(["page two"])

        monkeypatch.setattr("pypdf.PdfReader", _fake_reader)

        extractor = PdfExtractor(recursive=True)
        result = extractor.extract_directory(tmp_path)

        assert result["summary"]["total"] == 2
        assert result["summary"]["success"] == 2
        assert result["summary"]["failed"] == 0

    def test_extract_directory_non_recursive(self, tmp_path: Path, monkeypatch):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "nested.pdf").write_bytes(b"fake")
        (tmp_path / "root.pdf").write_bytes(b"fake")

        monkeypatch.setattr(
            "pypdf.PdfReader",
            lambda _p: _make_fake_reader(["text"]),
        )

        extractor = PdfExtractor(recursive=False)
        result = extractor.extract_directory(tmp_path)

        assert result["summary"]["total"] == 1
        filenames = [f["filename"] for f in result["files"]]
        assert "root.pdf" in filenames
        assert "nested.pdf" not in filenames

    def test_extract_directory_not_a_directory(self, tmp_path: Path):
        extractor = PdfExtractor()
        with pytest.raises(ValueError, match="Not a directory"):
            extractor.extract_directory(tmp_path / "does-not-exist")

    def test_max_chars_truncation(self, tmp_path: Path, monkeypatch):
        pdf_path = tmp_path / "long.pdf"
        pdf_path.write_bytes(b"fake")

        monkeypatch.setattr(
            "pypdf.PdfReader",
            lambda _p: _make_fake_reader(["abcdefghij"]),
        )

        extractor = PdfExtractor(max_chars=5)
        result = extractor.extract_file(pdf_path)

        assert result["status"] == "success"
        assert result["text"] == "abcde"
