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
