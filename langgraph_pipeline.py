#!/usr/bin/env python3
"""
LangGraph pipeline wiring for the AI-powered web crawler.
Provides a minimal sequential graph: crawl -> process -> write.
Falls back gracefully if LangGraph is unavailable.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List

from config import CrawlerConfig
from database_enhanced import EnhancedCrawlerDatabase
from crawler import WebCrawler
from content_processor import ContentProcessor
from llm_normalizer import LLMNormalizer
from obsidian_writer import ObsidianWriter


def _process_pages(db: EnhancedCrawlerDatabase, llm_normalizer: Optional[LLMNormalizer] = None, use_llm: bool = True) -> Dict[str, Any]:
    """Local copy of page processing to avoid circular imports."""
    from tqdm import tqdm  # lazy import to keep import graph light

    unprocessed = db.get_unprocessed_pages(limit=1000)
    processed_count = 0

    for page in tqdm(unprocessed, desc="Processing pages"):
        url = page['url']
        html_content = page['content']
        if not html_content:
            continue

        processed = ContentProcessor.extract_content(html_content, url)
        metadata = {'tags': [CrawlerConfig.TAG_PREFIX]}
        summary = ''
        page_type = ''
        lang = 'en'

        if use_llm and llm_normalizer:
            try:
                improved_title = llm_normalizer.improve_title(
                    processed['title'], processed['content'][:500]
                )
                processed['title'] = improved_title
                metadata['tags'] = llm_normalizer.extract_tags(improved_title, processed['content'])
                summary = llm_normalizer.summarize(improved_title, processed['content'])
                page_type, lang = llm_normalizer.classify(improved_title, processed['content'])
            except Exception as e:  # non-blocking
                print(f"⚠️  LLM processing failed for {url}: {e}")

        processed['metadata'] = metadata

        page_data = {
            'title': processed['title'],
            'slug': processed['slug'],
            'content': processed['content'],
            'markdown_content': processed['markdown_content'],
            'word_count': processed['word_count'],
            'content_hash': processed['checksum'],
            'depth': page['crawl_depth'],
            'metadata': processed['metadata'],
            'status': 'processed',
            'summary': summary,
            'type': page_type,
            'lang': lang,
        }
        db.upsert_page_enhanced(url, page_data)
        if processed['links']:
            db.add_links(url, processed['links'])
        processed_count += 1

    return {"processed_count": processed_count}


def _write_vault(db: EnhancedCrawlerDatabase, writer: ObsidianWriter) -> Dict[str, Any]:
    from tqdm import tqdm
    processed_pages: List[dict] = []
    all_urls = db.get_all_urls()

    for url in tqdm(all_urls, desc="Loading pages"):
        page = db.get_page(url)
        if page and page.get('processed') and not page.get('written_to_vault'):
            processed_pages.append(page)

    written = 0
    for page in tqdm(processed_pages, desc="Writing files"):
        try:
            backlinks = db.get_backlinks(page['url'])
            writer.write_page(page, backlinks)
            db.mark_page_processed(page['url'], written=True)
            written += 1
        except Exception as e:
            print(f"❌ Failed to write {page['url']}: {e}")

    return {"written": written}


def run_pipeline(
    use_langgraph: bool,
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
    """Run the pipeline either via LangGraph (if requested and available) or sequentially."""
    # Apply overrides
    if seeds:
        CrawlerConfig.SEED_URLS = seeds
    if max_pages:
        CrawlerConfig.MAX_PAGES = max_pages
    if max_depth:
        CrawlerConfig.MAX_DEPTH = max_depth
    if vault_dir:
        from pathlib import Path
        CrawlerConfig.VAULT_DIR = Path(vault_dir)
    if allowed_domains:
        CrawlerConfig.ALLOWED_DOMAINS = allowed_domains
    if docs_prefix:
        CrawlerConfig.DOCS_PATH_PREFIX = docs_prefix

    # Optionally run docs discovery to expand seeds
    if full_docs and CrawlerConfig.SEED_URLS:
        from discovery_module import discover_docs_urls
        expanded: List[str] = []
        for s in CrawlerConfig.SEED_URLS:
            try:
                expanded.extend(
                    discover_docs_urls(
                        base_url=s,
                        restrict_prefix=docs_prefix,
                        allowed_domains=CrawlerConfig.ALLOWED_DOMAINS,
                        max_urls=CrawlerConfig.MAX_PAGES * 10,
                        timeout=CrawlerConfig.REQUEST_TIMEOUT,
                    )
                )
            except Exception:
                continue
        # Deduplicate while preserving order
        seen = set()
        CrawlerConfig.SEED_URLS = [u for u in (expanded or CrawlerConfig.SEED_URLS) if not (u in seen or seen.add(u))]

    # Validate and prepare runtime dirs
    if not CrawlerConfig.validate():
        raise SystemExit("Invalid configuration. Check environment/CLI args.")

    # Initialize components
    db = EnhancedCrawlerDatabase(CrawlerConfig.DATABASE_PATH)
    crawler = WebCrawler(db, CrawlerConfig)
    writer = ObsidianWriter(CrawlerConfig.VAULT_DIR)

    llm_normalizer: Optional[LLMNormalizer] = None
    if not skip_llm:
        try:
            print("🤖 Initializing LLM normalizer (LM Studio)...")
            llm_normalizer = LLMNormalizer(CrawlerConfig, db=db)
            print("✅ LLM ready")
        except Exception as e:
            print(f"⚠️  LLM initialization failed: {e}\nContinuing without LLM enhancement…")

    # If not using LangGraph, run sequentially
    if not use_langgraph:
        if not resume:
            print("\n🕷️  Phase 1: Crawling")
            crawler.initialize(CrawlerConfig.SEED_URLS)
            pages_crawled = crawler.run()
            print(f"✅ Crawled {pages_crawled} pages")
        print("\n🔄 Phase 2: Processing")
        p = _process_pages(db, llm_normalizer, use_llm=not skip_llm)
        print("\n📝 Phase 3: Writing Obsidian Vault")
        w = _write_vault(db, writer)
        return {"mode": "sequential", "processed": p.get("processed_count", 0), "written": w.get("written", 0)}

    # LangGraph mode
    try:
        from langgraph.graph import StateGraph, START, END
    except Exception as e:
        print(f"⚠️  LangGraph unavailable ({e}); falling back to sequential mode.")
        return run_pipeline(False, seeds, max_pages, max_depth, skip_llm, resume)

    state_graph = StateGraph(dict)

    def crawl_node(state: Dict[str, Any]) -> Dict[str, Any]:
        if not resume:
            print("\n🕷️  Phase 1: Crawling (LangGraph)")
            crawler.initialize(CrawlerConfig.SEED_URLS)
            crawled = crawler.run()
        else:
            print("▶️  Resuming from previous crawl (LangGraph)")
            crawled = 0
        return {**state, "crawled": crawled}

    def process_node(state: Dict[str, Any]) -> Dict[str, Any]:
        print("\n🔄 Phase 2: Processing (LangGraph)")
        p = _process_pages(db, llm_normalizer, use_llm=not skip_llm)
        return {**state, **p}

    def write_node(state: Dict[str, Any]) -> Dict[str, Any]:
        print("\n📝 Phase 3: Writing Obsidian Vault (LangGraph)")
        w = _write_vault(db, writer)
        return {**state, **w}

    state_graph.add_node("crawl", crawl_node)
    state_graph.add_node("process", process_node)
    state_graph.add_node("write", write_node)
    state_graph.add_edge(START, "crawl")
    state_graph.add_edge("crawl", "process")
    state_graph.add_edge("process", "write")
    state_graph.add_edge("write", END)

    app = state_graph.compile()
    result = app.invoke({})
    result["mode"] = "langgraph"
    return result