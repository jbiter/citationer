#!/usr/bin/env python3
"""Build or serve the docs site.

Usage:
  python site/manage.py build   # Build static site to site/build/
  python site/manage.py serve   # Serve at http://localhost:8000
  python site/manage.py deploy  # Build and push to gh-pages
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def serve(port: int = 8000) -> None:
    site_dir = Path(__file__).parent / "build"
    if not site_dir.exists():
        print("No build directory; run 'build' first.")
        return
    os.chdir(site_dir)
    print(f"Serving docs at http://localhost:{port}")
    HTTPServer(("", port), SimpleHTTPRequestHandler).serve_forever()


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        try:
            subprocess.run(
                ["mkdocs", "build", "--clean"],
                cwd=Path(__file__).parent,
                check=True,
            )
            print("✓ Built to site/build/")
        except FileNotFoundError:
            print("mkdocs not installed; pip install mkdocs-material")
    elif cmd == "serve":
        serve()
    elif cmd == "deploy":
        try:
            subprocess.run(
                ["mkdocs", "gh-deploy"],
                cwd=Path(__file__).parent,
                check=True,
            )
        except FileNotFoundError:
            print("mkdocs not installed")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
