#!/usr/bin/env python3
"""
Semantic linker that computes "See also" candidates via EmbeddingsManager
and returns frontmatter-friendly entries.
"""
from __future__ import annotations

from typing import List, Dict

from config import CrawlerConfig
from embeddings_manager import EmbeddingsManager


def build_semantic_links(config: CrawlerConfig, page_id: str, content: str) -> List[Dict]:
    em = EmbeddingsManager(config)
    sims = em.query_similar(
        content=content,
        top_k=config.SEMANTIC_TOP_K,
        threshold=config.SEMANTIC_THRESHOLD,
        exclude_ids=[page_id],
    )
    # Map to simple objects for frontmatter and "See also" sections
    results: List[Dict] = []
    for s in sims:
        results.append({"id": s["id"], "score": round(float(s["score"]), 3)})
    return results
