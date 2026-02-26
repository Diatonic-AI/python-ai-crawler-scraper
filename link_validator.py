#!/usr/bin/env python3
"""
Link validator for internal wiki-links and external URLs.
- Internal: verify that target slug exists; return missing slugs list.
- External: HEAD (fallback GET) with retries and simple rate limit.
Never raises; returns structured results.
"""
from __future__ import annotations

import re
import time
from typing import Dict, List, Set
from urllib.parse import urlparse

import requests

from config import CrawlerConfig


WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def find_wikilinks(markdown: str) -> List[str]:
    return [m.group(1).strip() for m in WIKILINK_RE.finditer(markdown)]


def validate_internal_wikilinks(markdown: str, existing_slugs: Set[str]) -> List[str]:
    missing: List[str] = []
    for target in find_wikilinks(markdown):
        slug = target.strip()
        if slug and slug not in existing_slugs:
            missing.append(slug)
    return sorted(set(missing))


def validate_external_links(urls: List[str], timeout: int, retries: int, rate_delay: float = 0.1) -> Dict[str, int]:
    results: Dict[str, int] = {}
    sess = requests.Session()
    headers = {"User-Agent": CrawlerConfig.USER_AGENT}
    for u in urls:
        code = 0
        for attempt in range(retries + 1):
            try:
                r = sess.head(u, timeout=timeout, allow_redirects=True, headers=headers)
                code = r.status_code
                if code >= 400:
                    # try GET as fallback
                    r = sess.get(u, timeout=timeout, allow_redirects=True, headers=headers, stream=True)
                    code = r.status_code
                break
            except Exception:
                code = 0
                time.sleep(rate_delay)
                continue
        results[u] = code
        time.sleep(rate_delay)
    return results
