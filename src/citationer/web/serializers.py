"""JSON 安全序列化辅助函数。"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any


def to_json_safe(obj: Any) -> Any:
    """递归转换 dataclass、Path、元组键字典为 JSON 安全类型。"""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return to_json_safe(dataclasses.asdict(obj))
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, dict):
        return {_json_key(k): to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_json_safe(v) for v in obj]
    return obj


def _json_key(key: Any) -> str:
    if isinstance(key, tuple):
        return "|".join(str(part) for part in key)
    return str(key)
