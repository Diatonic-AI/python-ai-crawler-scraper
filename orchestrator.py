#!/usr/bin/env python3
"""
Orchestrator entrypoints for running the crawler with or without LangGraph.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from langgraph_pipeline import run_pipeline


def run_with_langgraph(
    seeds: Optional[List[str]] = None,
    max_pages: Optional[int] = None,
    max_depth: Optional[int] = None,
    skip_llm: bool = False,
    resume: bool = False,
    vault_dir: Optional[str] = None,
    allowed_domains: Optional[List[str]] = None,
    docs_prefix: Optional[str] = None,
    full_docs: bool = False,
) -> Dict[str, Any]:
    """Run the pipeline via LangGraph; falls back to sequential if LangGraph missing."""
    return run_pipeline(True, seeds, max_pages, max_depth, skip_llm, resume, vault_dir, allowed_domains, docs_prefix, full_docs)


def run_sequential(
    seeds: Optional[List[str]] = None,
    max_pages: Optional[int] = None,
    max_depth: Optional[int] = None,
    skip_llm: bool = False,
    resume: bool = False,
    vault_dir: Optional[str] = None,
    allowed_domains: Optional[List[str]] = None,
    docs_prefix: Optional[str] = None,
    full_docs: bool = False,
) -> Dict[str, Any]:
    """Run the pipeline sequentially without LangGraph."""
    return run_pipeline(False, seeds, max_pages, max_depth, skip_llm, resume, vault_dir, allowed_domains, docs_prefix, full_docs)
