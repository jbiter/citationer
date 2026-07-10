# Contributing

Citationer is open source under the MIT license. Contributions are welcome.

## Development setup

```bash
git clone https://github.com/jbiter/citationer.git
cd citationer
pip install --no-build-isolation -e ".[all,dev]"
```

## Running tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/citationer --cov-report=term-missing
```

## Code style

- Lint: `ruff check src/ tests/`
- Type check: `mypy src/`
- Format: `ruff format src/ tests/`

## Adding a parser

Citationer uses a pluggable parser system. To add a new source:

1. Create `src/citationer/parsers/<name>.py` with a class that inherits from `BaseParser`:

```python
from citationer.parsers.base import BaseParser

class MySourceParser(BaseParser):
    @property
    def source_name(self) -> str:
        return "MySource"

    def detect(self, filepath):
        # Return True if this parser can handle the file
        ...

    def parse(self, filepath):
        # Return list[Record]
        ...
```

2. Register the parser in `src/citationer/cli/scan_cmd.py` (see `get_registry` function).

3. Add the parser to `src/citationer/parsers/__init__.py` for direct imports.

## Adding a CLI command

Create a new `src/citationer/cli/<name>_cmd.py` with a Typer `app`:

```python
import typer
app = typer.Typer(name="mycmd", help="...")
```

Register the import function in `src/citationer/cli/main.py` and add it to the `_register` function.

## Pull request process

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Ensure `ruff`, `mypy`, and `pytest` all pass
5. Submit a PR with a clear description

## Reporting issues

Use [GitHub Issues](https://github.com/jbiter/citationer/issues) to report bugs or request features.
