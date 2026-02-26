#!/usr/bin/env python3
"""
Discovery helpers: sitemap.xml and RSS/Atom feeds.
Return additional candidate URLs for seeding/frontier.
"""
from __future__ import annotations

from typing import List, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import feedparser


def discover_from_homepage(home_url: str, timeout: int = 20) -> List[str]:
    urls: Set[str] = set()
    try:
        r = requests.get(home_url, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for link in soup.find_all("link", rel=True, href=True):
            rel = " ".join(link.get("rel", [])).lower()
            href = link.get("href")
            if not href:
                continue
            abs_url = urljoin(home_url, href)
            if "alternate" in rel and any(t in (link.get("type") or "").lower() for t in ["rss", "atom", "xml"]):
                urls.add(abs_url)
    except Exception:
        pass
    # try conventional feed paths
    for suffix in ["/feed/", "/rss", "/atom.xml"]:
        urls.add(urljoin(home_url, suffix))
    return list(urls)


def discover_from_sitemap(base_url: str, timeout: int = 20) -> List[str]:
    """Fetch /sitemap.xml and parse <loc> entries (best-effort)."""
    results: List[str] = []
    parsed = urlparse(base_url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    try:
        r = requests.get(sitemap_url, timeout=timeout)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "xml")
        for loc in soup.find_all("loc"):
            if loc.text:
                results.append(loc.text.strip())
    except Exception:
        return []
    return results


def discover_urls(seed: str, timeout: int = 20) -> List[str]:
    """Aggregate discovery from sitemap and homepage feeds."""
    urls: Set[str] = set()
    urls.update(discover_from_sitemap(seed, timeout=timeout))
    for feed_url in discover_from_homepage(seed, timeout=timeout):
        try:
            fp = feedparser.parse(feed_url)
            for e in fp.entries[:200]:
                link = getattr(e, "link", None)
                if link:
                    urls.add(link)
        except Exception:
            continue
    return list(urls)


def discover_docs_urls(
    base_url: str,
    restrict_prefix: str | None = None,
    allowed_domains: List[str] | None = None,
    max_urls: int = 500,
    timeout: int = 20,
) -> List[str]:
    """
    Best-effort crawl of documentation URLs starting at base_url.
    - Stay on the same netloc.
    - If restrict_prefix is provided, only include paths starting with that prefix.
    - BFS over internal <a href> links until max_urls is reached.
    """
    from collections import deque

    parsed_seed = urlparse(base_url)
    netloc = parsed_seed.netloc
    scheme = parsed_seed.scheme
    prefix = restrict_prefix or ""

    if allowed_domains:
        # ensure requested netloc is included
        if netloc not in allowed_domains:
            allowed_domains = list(set(allowed_domains + [netloc]))

    seen: Set[str] = set()
    out: List[str] = []
    q = deque([base_url])

    def is_allowed(u: str) -> bool:
        p = urlparse(u)
        if p.scheme not in ("http", "https"):
            return False
        if p.netloc != netloc:
            return False
        if allowed_domains and p.netloc not in allowed_domains:
            return False
        if prefix:
            return p.path.startswith(prefix)
        return True

    while q and len(out) < max_urls:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        try:
            r = requests.get(cur, timeout=timeout)
            if r.status_code != 200 or "text/html" not in (r.headers.get("Content-Type") or ""):
                continue
            out.append(cur)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a.get("href")
                abs_url = urljoin(cur, href)
                if is_allowed(abs_url) and abs_url not in seen:
                    q.append(abs_url)
                    if len(out) + len(q) >= max_urls:
                        break
        except Exception:
            continue
    return out
