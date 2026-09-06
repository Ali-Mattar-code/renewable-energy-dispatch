"""Machine-readable output helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(payload: dict[str, Any], destination: str | Path) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
