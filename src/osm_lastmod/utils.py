from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, List, Optional


def safe_int(x: str) -> Optional[int]:
    try:
        x = (x or "").strip()
        if not x:
            return None
        return int(float(x))
    except Exception:
        return None


def iso_to_dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def fmt_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    # store as naive local-like timestamp string
    dt_naive = dt.replace(tzinfo=None)
    return dt_naive.strftime("%Y-%m-%d %H:%M:%S")


def host_from_url(url: str) -> str:
    try:
        return url.split("//", 1)[-1].split("/", 1)[0]
    except Exception:
        return url


def chunked(items: List[Any], n: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), n):
        yield items[i:i + n]
