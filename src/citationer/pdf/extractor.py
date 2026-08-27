"""PDF text extraction engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class PdfExtractor:
    """Extract text from a directory of PDF files."""

    def __init__(self, recursive: bool = True, max_chars: int = 0) -> None:
        self.recursive = recursive
        self.max_chars = max_chars

    def extract_directory(self, directory: Path) -> dict[str, Any]:
        """Extract text from all PDF files under *directory*."""
        directory = directory.resolve()
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        pattern = "**/*.pdf" if self.recursive else "*.pdf"
        pdf_files = sorted(directory.glob(pattern))

        files: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for filepath in pdf_files:
            result = self.extract_file(filepath)
            if result["status"] == "success":
                files.append(result)
            else:
                errors.append(result)

        return {
            "files": files,
            "errors": errors,
            "summary": {
                "total": len(files) + len(errors),
                "success": len(files),
                "failed": len(errors),
            },
        }

    def extract_file(self, filepath: Path) -> dict[str, Any]:
        """Extract text from a single PDF file."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(filepath))
            text_parts: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

            full_text = "\n".join(text_parts).strip()
            if self.max_chars > 0:
                full_text = full_text[: self.max_chars]

            return {
                "filename": filepath.name,
                "path": str(filepath),
                "page_count": len(reader.pages),
                "word_count": len(full_text.split()),
                "text": full_text,
                "status": "success",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "filename": filepath.name,
                "path": str(filepath),
                "error": str(exc),
                "status": "error",
            }
