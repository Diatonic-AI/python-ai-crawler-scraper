#!/usr/bin/env python3
"""
Robots.txt policy helper with basic Disallow and Crawl-delay support.
Caches per-host robots files and exposes allow/deny checks and delays.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import urlparse

import requests


@dataclass
class _RobotsRecord:
    fetched_at: float
    allow: object  # placeholder for future expansion
    crawl_delay: Optional[float]
    raw: str


class RobotsPolicy:
    def __init__(self, user_agent: str, fallback_delay: float = 1.0, enabled: bool = True) -> None:
        self.user_agent = user_agent or "*"
        self.fallback_delay = fallback_delay
        self.enabled = enabled
        self._cache: Dict[str, _RobotsRecord] = {}
        self._ttl_sec = 12 * 3600  # 12h cache

    def _fetch(self, base_url: str) -> _RobotsRecord:
        host = urlparse(base_url).netloc
        now = time.time()
        # return cached if fresh
        rec = self._cache.get(host)
        if rec and now - rec.fetched_at < self._ttl_sec:
            return rec
        robots_url = f"{urlparse(base_url).scheme}://{host}/robots.txt"
        raw = ""
        try:
            r = requests.get(robots_url, timeout=10)
            if r.status_code == 200:
                raw = r.text
        except Exception:
            raw = ""
        crawl_delay = self._parse_crawl_delay(raw)
        new_rec = _RobotsRecord(fetched_at=now, allow=object(), crawl_delay=crawl_delay, raw=raw)
        self._cache[host] = new_rec
        return new_rec

    @staticmethod
    def _parse_crawl_delay(raw: str) -> Optional[float]:
        # Very simple UA-agnostic crawl-delay parser; prefer UA-matched but keep simple
        if not raw:
            return None
        m = re.search(r"(?im)^\s*crawl-delay\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*$", raw)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
        return None

    @staticmethod
    def _is_disallowed(raw: str, url: str, user_agent: str) -> bool:
        # Minimal Disallow handling: honor lines within nearest UA section or wildcard
        if not raw:
            return False
        path = urlparse(url).path or "/"
        # Extract groups
        groups = re.split(r"(?i)^user-agent:\s*", raw)
        ua_rules: Dict[str, list] = {}
        for g in groups:
            lines = [l.strip() for l in g.splitlines() if l.strip()]
            if not lines:
                continue
            ua = lines[0].lower()
            disallows = []
            for ln in lines[1:]:
                if ln.lower().startswith("disallow:"):
                    rule = ln.split(":", 1)[1].strip()
                    disallows.append(rule)
            if disallows:
                ua_rules.setdefault(ua, []).extend(disallows)
        # choose rules by UA or fallback to '*'
        rules = ua_rules.get(user_agent.lower()) or ua_rules.get("*") or []
        for rule in rules:
            if not rule:  # empty disallow means allow all
                continue
            if path.startswith(rule):
                return True
        return False

    def is_allowed(self, url: str) -> bool:
        if not self.enabled:
            return True
        rec = self._fetch(url)
        return not self._is_disallowed(rec.raw, url, self.user_agent)

    def get_crawl_delay(self, url: str) -> float:
        if not self.enabled:
            return 0.0
        rec = self._fetch(url)
        return float(rec.crawl_delay) if rec.crawl_delay is not None else float(self.fallback_delay)
