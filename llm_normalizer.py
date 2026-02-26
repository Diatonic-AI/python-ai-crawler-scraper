#!/usr/bin/env python3
"""
LLM-based normalizer using LM Studio via langchain_openai.
Adds support for title improvement, tags, summary, page classification, and language.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from config import CrawlerConfig
from llm_client import LLMClient


class LLMNormalizer:
    """Uses local LLM (LM Studio) to normalize and enrich content."""

    def __init__(self, config: CrawlerConfig, db=None):
        self.config = config
        self.client = LLMClient(config, db=db)

    def improve_title(self, title: str, content_preview: str) -> str:
        return self.client.improve_title(title, content_preview)

    def extract_tags(self, title: str, content: str) -> List[str]:
        return self.client.extract_tags(title, content)

    def summarize(self, title: str, content: str) -> str:
        return self.client.summarize(title, content)

    def classify(self, title: str, content: str) -> Tuple[str, str]:
        return self.client.classify_page(title, content)
