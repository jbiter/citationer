"""Filter expression parser and matcher for `citationer query`.

The DSL supports a limited set of fields and operators to keep evaluation
safe (no `eval()` on user input).  Composed with AND/OR connectives.

Grammar (informal):

    expr    := term ( (AND|OR) term )*
    term    := field OP value
    field   := one of the allowed fields below
    OP      := '=' | '!=' | '>' | '<' | '>=' | '<=' | 'contains'
    value   := number | quoted-string

Allowed fields map onto Record attributes.  See `_FIELD_GETTERS` for
the mapping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from citationer.models.record import Record

# ---------------------------------------------------------------------------
# Public data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Filter:
    """A single parsed filter term: `<field> <op> <value>`."""

    field: str
    op: str
    value: str


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------


# Maps DSL field names → callables that extract the value from a Record.
# `author` and `keyword` resolve to *lists*; the matcher applies "contains"
# across any element.
_FIELD_GETTERS: dict[str, Any] = {
    "year": lambda r: r.year,
    "journal": lambda r: r.journal,
    "author": lambda r: [a.full_name for a in r.authors],
    "keyword": lambda r: list(r.keywords) + list(r.keywords_en or []),
    "doc_type": lambda r: r.doc_type.value if r.doc_type else None,
    "language": lambda r: r.language,
    "citation_count": lambda r: r.citation_count,
}

# Operator handlers: (record_value, filter_value) -> bool
_OPS: dict[str, Any] = {
    "=": lambda v, f: v == _coerce(f, v),
    "!=": lambda v, f: v != _coerce(f, v),
    ">": lambda v, f: _cmp(v, f) > 0,
    "<": lambda v, f: _cmp(v, f) < 0,
    ">=": lambda v, f: _cmp(v, f) >= 0,
    "<=": lambda v, f: _cmp(v, f) <= 0,
    "contains": lambda v, f: _contains(v, f),
}


# ---------------------------------------------------------------------------
# Coercion / comparison helpers
# ---------------------------------------------------------------------------


def _coerce(filter_value: str, record_value: Any) -> Any:
    """Coerce a filter string into a value comparable with record_value.

    Booleans are normalised; ints/floats are parsed so that
    `year=2024` matches a Record whose `year=2024` (an int).
    """
    if isinstance(record_value, bool):
        return filter_value.lower() in ("true", "1", "yes")
    if isinstance(record_value, int) and not isinstance(record_value, bool):
        try:
            return int(filter_value)
        except ValueError:
            return filter_value
    if isinstance(record_value, float):
        try:
            return float(filter_value)
        except ValueError:
            return filter_value
    return filter_value


def _cmp(record_value: Any, filter_value: str) -> int:
    """Three-way comparison that returns 0 if the record value is None
    (missing data: cannot satisfy >/>=).

    None on the right side (filter value missing) compares as greater
    than anything, so missing data does not accidentally match `>0`.
    """
    if record_value is None:
        return -1
    try:
        return (record_value > _coerce(filter_value, record_value)) - (
            record_value < _coerce(filter_value, record_value)
        )
    except TypeError:
        # Strings vs ints: fall back to string compare
        return (str(record_value) > filter_value) - (str(record_value) < filter_value)


def _contains(record_value: Any, filter_value: str) -> bool:
    """`contains` works for both list and scalar record values."""
    if record_value is None:
        return False
    needle = filter_value.lower()
    if isinstance(record_value, (list, tuple, set)):
        return any(needle in str(v).lower() for v in record_value)
    return needle in str(record_value).lower()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


_TERM_RE = re.compile(
    r"""
    \s*                                  # leading whitespace
    (?P<field>[A-Za-z_]\w*)              # field name
    \s*
    (?P<op>=|!=|>=|<=|>|<|contains)      # operator
    \s*
    (?:                                   # value (number or quoted string)
        "(?P<dqval>[^"]*)"
        | '(?P<sqval>[^']*)'
        | (?P<bare>[^\s()]+)              # unquoted token
    )
    \s*
    """,
    re.VERBOSE,
)

# OR is a connectives, not a filter.  We model the connectives as
# a single Token stream: filters interleaved with "AND"/"OR" sentinels.
_AND_OR = ("AND", "OR")


def parse_filter(expr: str) -> list:
    """Parse a filter expression into a list of filters + connectives.

    Connectives ("AND" / "OR") are returned as plain strings in the
    list, mixed with Filter instances.  The matcher walks the list and
    applies the most recent connective between filters.
    """
    tokens: list = []
    remaining = expr.strip()
    if not remaining:
        return tokens

    # Split by AND/OR (case-sensitive uppercase), keeping the delimiter.
    # We do this by tokenizing with a regex over the input.
    pos = 0
    while pos < len(remaining):
        # Skip whitespace and parens (grouping is implicit via AND/OR
        # precedence; parens are accepted for readability only).
        while pos < len(remaining) and remaining[pos] in " \t()":
            pos += 1
        if pos >= len(remaining):
            break

        m = _TERM_RE.match(remaining, pos)
        if not m:
            # Try to swallow a connective keyword
            head = remaining[pos:].lstrip()
            if head.startswith(_AND_OR):
                kw = head.split()[0]
                tokens.append(kw)
                pos = len(remaining) - len(head) + len(kw)
                continue
            raise ValueError(f"Invalid filter expression near: {remaining[pos:pos+20]!r}")
        field = m.group("field")
        op = m.group("op")
        value = m.group("dqval")
        if value is None:
            value = m.group("sqval")
        if value is None:
            value = m.group("bare")
        if field not in _FIELD_GETTERS:
            raise ValueError(
                f"Unknown field {field!r}. Allowed: {sorted(_FIELD_GETTERS)}"
            )
        if op not in _OPS:
            raise ValueError(f"Invalid operator {op!r}")
        tokens.append(Filter(field, op, value))
        pos = m.end()
        # Allow optional AND/OR between terms
        head = remaining[pos:].lstrip()
        for kw in _AND_OR:
            if head.startswith(kw + " ") or head == kw:
                tokens.append(kw)
                pos = len(remaining) - len(head) + len(kw)
                break
    return tokens


# ---------------------------------------------------------------------------
# Matcher
# ---------------------------------------------------------------------------


def matches(record: Record, filters: list) -> bool:
    """Return True iff `record` satisfies the filter list.

    Filter list mixes Filter instances with "AND" / "OR" string
    connectives (as produced by `parse_filter`).  An empty list
    matches all records.
    """
    if not filters:
        return True
    result: bool | None = None
    op = "AND"
    for token in filters:
        if token == "OR":
            op = "OR"
            continue
        if token == "AND":
            op = "AND"
            continue
        assert isinstance(token, Filter)
        getter = _FIELD_GETTERS.get(token.field)
        if getter is None:
            return False  # unknown field -> never matches
        record_value = getter(record)
        handler = _OPS.get(token.op)
        if handler is None:
            return False
        match = handler(record_value, token.value)
        if result is None:
            result = match
        elif op == "OR":
            result = result or match
        else:  # AND (default)
            result = result and match
    return bool(result)
