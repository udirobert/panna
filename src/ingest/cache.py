"""Read-through disk cache for provider payloads.

Finished-match data is immutable (a StatsBomb events file never changes
once the whistle blows), so it caches forever. Indexes and live fixtures
get short TTLs. Fail-soft by contract: a broken cache dir or unreadable
entry degrades to a live fetch — the cache can never take ingest down.

Layout: ``$PANNA_INGEST_CACHE_DIR/<namespace>/<key>.json``
(default ``.cache/ingest``). ``PANNA_INGEST_CACHE=off`` disables reads and
writes entirely.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

DIR = Path(os.getenv("PANNA_INGEST_CACHE_DIR", ".cache/ingest"))

# per-namespace freshness: finished-match event files are immutable,
# indexes grow as seasons fill, live fixtures change minute to minute
TTL: dict[str, float | None] = {
    "statsbomb-events": None,  # immutable
    "statsbomb-matches": 86_400,  # 24h — index can grow
    "sportmonks": 300,  # 5m — a live fixture's timeline updates
}

_DISABLED = os.getenv("PANNA_INGEST_CACHE", "").lower() == "off"


def _path(namespace: str, key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(key))
    return DIR / namespace / f"{safe}.json"


def read(namespace: str, key: str) -> Any | None:
    if _DISABLED:
        return None
    p = _path(namespace, key)
    try:
        ttl = TTL.get(namespace, 300)
        if ttl is not None and time.time() - p.stat().st_mtime > ttl:
            return None
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001 — unreadable entry = miss
        return None


def write(namespace: str, key: str, data: Any) -> None:
    if _DISABLED:
        return
    try:
        p = _path(namespace, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(p)
    except Exception:  # noqa: BLE001 — a failed write just means next call refetches
        return
