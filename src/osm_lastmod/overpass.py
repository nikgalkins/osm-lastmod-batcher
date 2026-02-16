from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Tuple

import requests


class OverpassClient:
    def __init__(
        self,
        urls: List[str],
        user_agent: str,
        request_timeout: Tuple[int, int],
        cooldown_429_min_s: float,
        cooldown_429_max_s: float,
        cooldown_504_min_s: float,
        cooldown_504_max_s: float,
    ) -> None:
        self.urls = urls
        self.user_agent = user_agent
        self.request_timeout = request_timeout
        self.cooldown_429_min_s = cooldown_429_min_s
        self.cooldown_429_max_s = cooldown_429_max_s
        self.cooldown_504_min_s = cooldown_504_min_s
        self.cooldown_504_max_s = cooldown_504_max_s

    def build_query_batch(self, relation_ids: List[int], timeout_s: int, recursion_depth: int) -> str:
        ids_csv = ",".join(str(i) for i in relation_ids)
        depth = max(1, int(recursion_depth))
        arrows = " ".join([">;"] * depth)
        return f"""
[out:json][timeout:{timeout_s}];
relation(id:{ids_csv});
(._; {arrows});
out meta;
""".strip()

    def post(self, session: requests.Session, query: str, max_retries: int = 8) -> Tuple[Dict[str, Any], str]:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        backoff = 2.0
        last_error: str | None = None

        for attempt in range(1, max_retries + 1):
            for url in self.urls:
                try:
                    r = session.post(
                        url,
                        data={"data": query},
                        headers=headers,
                        timeout=self.request_timeout,
                    )

                    if r.status_code == 429:
                        last_error = f"HTTP 429 from {url}"
                        cooldown = random.uniform(self.cooldown_429_min_s, self.cooldown_429_max_s)
                        time.sleep(cooldown)
                        backoff = min(backoff * 1.5, 60.0)
                        continue

                    if r.status_code == 504:
                        last_error = f"HTTP 504 from {url}"
                        cooldown = random.uniform(self.cooldown_504_min_s, self.cooldown_504_max_s)
                        time.sleep(cooldown)
                        continue

                    r.raise_for_status()

                    ctype = (r.headers.get("Content-Type") or "").lower()
                    if "application/json" not in ctype:
                        snippet = (r.text or "")[:200].replace("\n", " ")
                        raise ValueError(f"Non-JSON response (Content-Type={ctype}). Snippet: {snippet}")

                    return r.json(), url

                except (requests.RequestException, ValueError) as e:
                    last_error = f"{url}: {e}"
                    sleep_s = backoff + random.random()
                    time.sleep(sleep_s)

            backoff = min(backoff * 1.8, 60.0)

        raise RuntimeError(f"Overpass request failed after retries: {last_error}")
