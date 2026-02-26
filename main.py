#!/usr/bin/env python3
"""
Main orchestration script for the AI-powered web crawler.
Coordinates crawling, processing, and Obsidian vault generation.
"""

import argparse
from pathlib import Path
from tqdm import tqdm

from config import CrawlerConfig
from database_enhanced import EnhancedCrawlerDatabase
from crawler import WebCrawler
from content_processor import ContentProcessor
from llm_normalizer import LLMNormalizer
from obsidian_writer import ObsidianWriter
from embeddings_manager import EmbeddingsManager
from semantic_linker import build_semantic_links
from markdown_linter import lint_and_format
from link_validator import validate_internal_wikilinks, validate_external_links, find_wikilinks


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='AI-Powered Web Crawler with Obsidian Output',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--seeds',
        nargs='+',
        help='Seed URLs to start crawling (overrides .env)'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum number of pages to crawl (overrides .env)'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        help='Maximum crawl depth (overrides .env)'
    )
    
    parser.add_argument(
        '--skip-llm',
        action='store_true',
        help='Skip LLM processing for faster crawling'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume previous crawl from database'
    )

    parser.add_argument(
        '--use-langgraph',
        action='store_true',
        help='Run the pipeline via LangGraph orchestration'
    )

    parser.add_argument(
        '--vault-dir',
        type=str,
        help='Override Obsidian vault output directory'
    )

    parser.add_argument(
        '--allowed-domains',
        nargs='+',
        help='Restrict crawl to these domains'
    )

    parser.add_argument(
        '--docs-prefix',
        type=str,
        help='Restrict docs discovery to URLs with this path prefix (e.g., /api-reference)'
    )

    parser.add_argument(
        '--full-docs',
        action='store_true',
        help='Discover all documentation URLs under the given seed (docs mode)'
    )
    
    return parser.parse_args()


def process_pages(db: EnhancedCrawlerDatabase, llm_normalizer: LLMNormalizer = None, use_llm: bool = True):
    """
    Process unprocessed pages: extract content, improve titles, generate markdown.
    
    Args:
        db: Database instance
        llm_normalizer: LLM normalizer instance (optional)
        use_llm: Whether to use LLM for enhancement
    """
    print("\n📝 Processing crawled pages...")
    
    unprocessed = db.get_unprocessed_pages(limit=1000)
    
    if not unprocessed:
        print("No unprocessed pages found.")
        return
    
    for page in tqdm(unprocessed, desc="Processing pages"):
        url = page['url']
        html_content = page['content']
        
        if not html_content:
            continue
        
        # Extract clean content
        processed = ContentProcessor.extract_content(html_content, url)
        metadata = {'tags': [CrawlerConfig.TAG_PREFIX]}
        summary = ''
        page_type = ''
        lang = 'en'
        
        # LLM enrichment if enabled
        if use_llm and llm_normalizer:
            try:
                improved_title = llm_normalizer.improve_title(
                    processed['title'], processed['content'][:500]
                )
                processed['title'] = improved_title
                metadata['tags'] = llm_normalizer.extract_tags(improved_title, processed['content'])
                summary = llm_normalizer.summarize(improved_title, processed['content'])
                page_type, lang = llm_normalizer.classify(improved_title, processed['content'])
            except Exception as e:
                print(f"⚠️  LLM processing failed for {url}: {e}")
        
        processed['metadata'] = metadata

        # Markdown lint/format (non-blocking)
        md_formatted, lint_notes = lint_and_format(processed['markdown_content'])
        processed['markdown_content'] = md_formatted

        # Build embeddings and semantic links (best-effort)
        semantic_similar = []
        try:
            em = EmbeddingsManager(CrawlerConfig)
            doc_id = processed['slug']
            em.upsert_page(doc_id, processed['content'], metadata={"url": url})
            semantic_similar = build_semantic_links(CrawlerConfig, doc_id, processed['content'])
        except Exception as e:
            print(f"⚠️  Embeddings/semantic failed for {url}: {e}")

        # Link validation (best-effort)
        missing_internal = []
        external_errors = []
        try:
            existing_slugs = set(db.get_all_slugs()) if hasattr(db, 'get_all_slugs') else set()
            missing_internal = validate_internal_wikilinks(processed['markdown_content'], existing_slugs)
            # crude external URL extraction
            import re
            ext_urls = re.findall(r"https?://[^\s)>'\]\"]+", processed['markdown_content'])
            ext_result = validate_external_links(ext_urls[:50], timeout=CrawlerConfig.EXTERNAL_LINK_TIMEOUT, retries=CrawlerConfig.EXTERNAL_LINK_RETRIES)
            external_errors = [f"{u} -> {code}" for u, code in ext_result.items() if code >= 400 or code == 0]
        except Exception as e:
            print(f"⚠️  Link validation failed for {url}: {e}")
        
        # Update database
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
            'semantic_similar': semantic_similar,
            'missing_internal_links': missing_internal,
            'external_link_errors': external_errors,
        }
        if lint_notes:
            page_data['metadata']['lint_notes'] = lint_notes
        
        # Use enhanced upsert method
        db.upsert_page_enhanced(url, page_data)
        
        # Store links
        if processed['links']:
            db.add_links(url, processed['links'])


def write_vault(db: EnhancedCrawlerDatabase, writer: ObsidianWriter):
    """
    Write processed pages to Obsidian vault.
    
    Args:
        db: Database instance
        writer: Obsidian writer instance
    """
    print("\n📚 Writing Obsidian vault...")
    
    # Get all processed pages
    processed_pages = []
    all_urls = db.get_all_urls()
    
    for url in tqdm(all_urls, desc="Loading pages"):
        page = db.get_page(url)
        if page and page.get('processed') and not page.get('written_to_vault'):
            processed_pages.append(page)
    
    if not processed_pages:
        print("No pages ready for vault writing.")
        return
    
    # Write each page
    for page in tqdm(processed_pages, desc="Writing files"):
        try:
            # Get backlinks
            backlinks = db.get_backlinks(page['url'])
            
            # Write to vault
            filepath = writer.write_page(page, backlinks)
            
            # Mark as written
            db.mark_page_processed(page['url'], written=True)
            
        except Exception as e:
            print(f"❌ Failed to write {page['url']}: {e}")
    
    print(f"\n✅ Wrote {len(processed_pages)} pages to vault: {writer.vault_dir}")


def main():
    """Main execution function."""
    args = parse_args()
    
    # Override config with CLI args
    if args.seeds:
        CrawlerConfig.SEED_URLS = args.seeds
    if args.max_pages:
        CrawlerConfig.MAX_PAGES = args.max_pages
    if args.max_depth:
        CrawlerConfig.MAX_DEPTH = args.max_depth
    
    # Apply optional overrides before validation
    if args.vault_dir:
        CrawlerConfig.VAULT_DIR = Path(args.vault_dir)
    if args.allowed_domains:
        CrawlerConfig.ALLOWED_DOMAINS = args.allowed_domains

    # Validate configuration
    if not CrawlerConfig.validate():
        print("❌ Invalid configuration. Please check your .env file or CLI args.")
        return 1
    
    # Display configuration
    CrawlerConfig.display()

    # Optional LangGraph path
    if args.use_langgraph:
        try:
            from orchestrator import run_with_langgraph
            result = run_with_langgraph(
                seeds=CrawlerConfig.SEED_URLS,
                max_pages=CrawlerConfig.MAX_PAGES,
                max_depth=CrawlerConfig.MAX_DEPTH,
                skip_llm=args.skip_llm,
                resume=args.resume,
                vault_dir=str(CrawlerConfig.VAULT_DIR),
                allowed_domains=CrawlerConfig.ALLOWED_DOMAINS,
                docs_prefix=args.docs_prefix,
                full_docs=args.full_docs,
            )
            print(f"\n✅ Pipeline completed ({result.get('mode')}). Processed={result.get('processed', 0)}, Written={result.get('written', 0)}")
            return 0
        except Exception as e:
            print(f"⚠️  LangGraph execution failed: {e}. Falling back to sequential mode…")

    # Initialize enhanced database with frontier, entities, and LLM tracking
    print(f"\n🗄️  Initializing enhanced database: {CrawlerConfig.DATABASE_PATH}")
    db = EnhancedCrawlerDatabase(CrawlerConfig.DATABASE_PATH)
    crawler = WebCrawler(db, CrawlerConfig)
    writer = ObsidianWriter(CrawlerConfig.VAULT_DIR)
    
    # Initialize LLM if not skipped
    llm_normalizer = None
    if not args.skip_llm:
        try:
            print("🤖 Initializing LLM normalizer (LM Studio)...")
            llm_normalizer = LLMNormalizer(CrawlerConfig, db=db)
            print("✅ LLM ready")
        except Exception as e:
            print(f"⚠️  LLM initialization failed: {e}")
            print("Continuing without LLM enhancement...")
    
    # Phase 1: Crawl
    if not args.resume:
        print("\n🕷️  Phase 1: Crawling")
        crawler.initialize(CrawlerConfig.SEED_URLS)
        pages_crawled = crawler.run()
        print(f"✅ Crawled {pages_crawled} pages")
    else:
        print("▶️  Resuming from previous crawl")
    
    # Show enhanced statistics
    stats = db.get_enhanced_statistics()
    print(f"\n📊 Enhanced Database Statistics:")
    print(f"  Total pages: {stats.get('total_pages', 0)}")
    print(f"  Processed: {stats.get('processed_pages', 0)}")
    print(f"  Unique sites: {stats.get('unique_sites', 0)}")
    print(f"  Total links: {stats.get('total_links', 0)}")
    print(f"  Total entities: {stats.get('total_entities', 0)}")
    print(f"  Frontier size: {stats.get('frontier_size', 0)}")
    
    # Show LLM stats if available
    llm_stats = stats.get('llm_operations', {})
    if llm_stats and llm_stats.get('total_ops', 0) > 0:
        print(f"  LLM operations: {llm_stats.get('total_ops', 0)} ({llm_stats.get('successful_ops', 0)} successful)")
    
    # Phase 2: Process
    print("\n🔄 Phase 2: Processing")
    process_pages(db, llm_normalizer, use_llm=not args.skip_llm)
    
    # Phase 3: Write vault
    print("\n📝 Phase 3: Writing Obsidian Vault")
    write_vault(db, writer)
    
    # Final enhanced statistics
    final_stats = db.get_enhanced_statistics()
    print(f"\n🎉 Crawl Complete!")
    print(f"  Total pages: {final_stats.get('total_pages', 0)}")
    print(f"  Processed pages: {final_stats.get('processed_pages', 0)}")
    print(f"  Total entities: {final_stats.get('total_entities', 0)}")
    print(f"  Vault location: {CrawlerConfig.VAULT_DIR}")
    print(f"  Database: {CrawlerConfig.DATABASE_PATH}")
    
    return 0


if __name__ == "__main__":
    exit(main())
