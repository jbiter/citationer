"""Module entry point — enables `python -m citationer` and PyInstaller binary."""

from citationer.cli.main import app


if __name__ == "__main__":
    app()
