#!/usr/bin/env python3
"""
Pydantic schema for Obsidian frontmatter validation.
Non-blocking: consumer may use this to validate and collect errors.
"""
from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class Frontmatter(BaseModel):
    title: str
    source_url: str = Field(default="")
    slug: str
    crawled_at: Optional[str] = None
    updated_at: Optional[str] = None
    crawl_depth: int = 0
    word_count: int = 0
    checksum: Optional[str] = None
    tags: List[str] = []
    summary: Optional[str] = None
    page_type: Optional[str] = None
    lang: Optional[str] = None
    embeddings_id: Optional[str] = None
    backlinks_count: Optional[int] = None
    outlinks_count: Optional[int] = None
    external_link_errors: List[str] = []
    missing_internal_links: List[str] = []
    semantic_similar: List[Dict] = []
    last_validated: Optional[str] = None
