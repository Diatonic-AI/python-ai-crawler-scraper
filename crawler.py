#!/usr/bin/env python3
"""
Core web crawling engine with URL queue management, domain filtering,
rate limiting, and robust error handling.
"""

import time
import requests
from urllib.parse import urljoin, urlparse
from collections import deque
from typing import Set, List, Dict, Optional, Tuple
import tldextract
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from config import CrawlerConfig
from database import CrawlerDatabase


class WebCrawler:
    """Manages web crawling with depth tracking and domain filtering."""
    
    def __init__(self, db: CrawlerDatabase, config: CrawlerConfig):
        """
        Initialize the web crawler.
        
        Args:
            db: Database instance for storing crawl data
            config: Configuration object with crawl settings
        """
        self.db = db
        self.config = config
        
        # URL queue: (url, depth) tuples
        self.queue = deque()
        
        # Tracking sets
        self.seen_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        
        # Request session with custom headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Domain filtering
        self.allowed_domains_set = set(config.ALLOWED_DOMAINS) if config.ALLOWED_DOMAINS else None
    
    def initialize(self, seed_urls: List[str]):
        """
        Initialize the crawler with seed URLs.
        
        Args:
            seed_urls: List of starting URLs to crawl
        """
        # Load already crawled URLs from database
        existing_urls = self.db.get_all_urls()
        self.crawled_urls.update(existing_urls)
        self.seen_urls.update(existing_urls)
        
        print(f"📊 Found {len(existing_urls)} URLs already in database")
        
        # Add seed URLs to queue
        for url in seed_urls:
            normalized_url = self._normalize_url(url)
            if normalized_url and normalized_url not in self.seen_urls:
                self.queue.append((normalized_url, 0))
                self.seen_urls.add(normalized_url)
                print(f"🌱 Added seed URL: {normalized_url}")
    
    def _normalize_url(self, url: str) -> Optional[str]:
        """
        Normalize URL by removing fragments and trailing slashes.
        
        Args:
            url: URL to normalize
        
        Returns:
            Normalized URL or None if invalid
        """
        try:
            parsed = urlparse(url)
            
            # Remove fragment
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Add query string if present
            if parsed.query:
                normalized += f"?{parsed.query}"
            
            # Remove trailing slash (except for root)
            if normalized.endswith('/') and len(parsed.path) > 1:
                normalized = normalized[:-1]
            
            return normalized
        
        except Exception as e:
            print(f"⚠️  Failed to normalize URL {url}: {e}")
            return None
    
    def _is_allowed_domain(self, url: str) -> bool:
        """
        Check if URL belongs to an allowed domain.
        
        Args:
            url: URL to check
        
        Returns:
            True if allowed, False otherwise
        """
        if not self.allowed_domains_set:
            # No domain restriction
            return True
        
        try:
            extracted = tldextract.extract(url)
            registered_domain = f"{extracted.domain}.{extracted.suffix}"
            
            return registered_domain in self.allowed_domains_set
        
        except Exception as e:
            print(f"⚠️  Failed to extract domain from {url}: {e}")
            return False
    
    def _should_skip_url(self, url: str) -> Tuple[bool, str]:
        """
        Determine if URL should be skipped based on extension or patterns.
        
        Args:
            url: URL to check
        
        Returns:
            Tuple of (should_skip: bool, reason: str)
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Check file extensions
        for ext in self.config.SKIP_EXTENSIONS:
            if path.endswith(ext):
                return True, f"Binary/media file: {ext}"
        
        # Skip common non-content paths
        skip_patterns = [
            '/api/', '/ajax/', '/json/', '/xml/',
            '/login', '/signin', '/signup', '/register',
            '/logout', '/auth/', '/oauth/',
            '/admin/', '/wp-admin/',
            '/feed/', '/rss/', '/atom/'
        ]
        
        for pattern in skip_patterns:
            if pattern in path:
                return True, f"Non-content path: {pattern}"
        
        return False, ""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, requests.Timeout))
    )
    def _fetch_url(self, url: str) -> Optional[requests.Response]:
        """
        Fetch URL content with retry logic.
        
        Args:
            url: URL to fetch
        
        Returns:
            Response object or None if fetch failed
        """
        try:
            response = self.session.get(
                url,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True,
                stream=True  # Stream to check content size before downloading
            )
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(ct in content_type for ct in ['text/html', 'application/xhtml']):
                print(f"⚠️  Skipping non-HTML content: {content_type}")
                return None
            
            # Check content size
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > self.config.MAX_CONTENT_SIZE:
                print(f"⚠️  Skipping large content: {content_length} bytes")
                return None
            
            # For HTML, get full content
            response.raise_for_status()
            
            return response
        
        except requests.Timeout:
            print(f"⏱️  Timeout fetching {url}")
            raise
        
        except requests.RequestException as e:
            print(f"❌ Request error fetching {url}: {e}")
            raise
        
        except Exception as e:
            print(f"❌ Unexpected error fetching {url}: {e}")
            return None
    
    def crawl_url(self, url: str, depth: int) -> Optional[Dict]:
        """
        Crawl a single URL and extract content and links.
        
        Args:
            url: URL to crawl
            depth: Current crawl depth
        
        Returns:
            Dictionary with crawl results or None if failed
        """
        # Check if URL should be skipped
        should_skip, reason = self._should_skip_url(url)
        if should_skip:
            print(f"⏭️  Skipping {url}: {reason}")
            return None
        
        # Fetch URL
        try:
            response = self._fetch_url(url)
            
            if not response:
                return None
            
            # Extract final URL after redirects
            final_url = self._normalize_url(response.url)
            
            return {
                'url': final_url,
                'original_url': url,
                'status_code': response.status_code,
                'content': response.text,
                'headers': dict(response.headers),
                'crawl_depth': depth
            }
        
        except Exception as e:
            print(f"❌ Failed to crawl {url}: {e}")
            return None
    
    def discover_links(self, base_url: str, html_content: str, current_depth: int) -> List[Tuple[str, int]]:
        """
        Discover and normalize links from HTML content.
        
        Args:
            base_url: Base URL for resolving relative links
            html_content: HTML content to parse
            current_depth: Current crawl depth
        
        Returns:
            List of (url, depth) tuples for discovered links
        """
        from bs4 import BeautifulSoup
        
        discovered = []
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').strip()
                
                # Skip empty, javascript, mailto, tel links
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                normalized_url = self._normalize_url(absolute_url)
                
                if not normalized_url:
                    continue
                
                # Check domain restriction
                if not self._is_allowed_domain(normalized_url):
                    continue
                
                # Check if already seen or should skip
                if normalized_url in self.seen_urls:
                    continue
                
                should_skip, _ = self._should_skip_url(normalized_url)
                if should_skip:
                    continue
                
                # Add to discovered links
                next_depth = current_depth + 1
                if next_depth <= self.config.MAX_DEPTH:
                    discovered.append((normalized_url, next_depth))
                    self.seen_urls.add(normalized_url)
        
        except Exception as e:
            print(f"⚠️  Error discovering links from {base_url}: {e}")
        
        return discovered
    
    def run(self) -> int:
        """
        Run the crawl until queue is empty or page limit is reached.
        
        Returns:
            Number of pages successfully crawled
        """
        pages_crawled = 0
        
        print(f"\n🚀 Starting crawl...")
        print(f"📊 Queue size: {len(self.queue)}")
        print(f"📊 Already crawled: {len(self.crawled_urls)}")
        
        while self.queue and pages_crawled < self.config.MAX_PAGES:
            url, depth = self.queue.popleft()
            
            # Skip if already crawled
            if url in self.crawled_urls:
                continue
            
            print(f"\n🔍 [{pages_crawled + 1}/{self.config.MAX_PAGES}] Crawling (depth {depth}): {url}")
            
            # Crawl the URL
            result = self.crawl_url(url, depth)
            
            if result:
                # Generate a temporary slug from URL to avoid collisions
                import hashlib
                url_hash = hashlib.sha256(result['url'].encode()).hexdigest()[:16]
                temp_slug = f"temp-{url_hash}"
                
                # Store in database (basic data for now)
                page_data = {
                    'title': '',  # Will be extracted by content processor
                    'slug': temp_slug,  # Temporary slug, will be regenerated during processing
                    'content': result['content'],
                    'crawl_depth': depth,
                    'metadata': {
                        'status_code': result['status_code'],
                        'original_url': result['original_url']
                    }
                }
                
                self.db.upsert_page(result['url'], page_data)
                
                # Discover new links
                new_links = self.discover_links(result['url'], result['content'], depth)
                
                if new_links:
                    print(f"  🔗 Discovered {len(new_links)} new links")
                    self.queue.extend(new_links)
                
                self.crawled_urls.add(result['url'])
                pages_crawled += 1
            
            # Rate limiting
            time.sleep(self.config.REQUEST_DELAY)
        
        print(f"\n✅ Crawl completed: {pages_crawled} pages")
        return pages_crawled


if __name__ == "__main__":
    # Test crawler
    from pathlib import Path
    from config import CrawlerConfig
    
    # Override config for testing
    CrawlerConfig.SEED_URLS = ["https://example.com"]
    CrawlerConfig.MAX_PAGES = 3
    CrawlerConfig.MAX_DEPTH = 1
    CrawlerConfig.REQUEST_DELAY = 2.0
    
    test_db = Path("test_crawler.db")
    db = CrawlerDatabase(test_db)
    
    crawler = WebCrawler(db, CrawlerConfig)
    crawler.initialize(CrawlerConfig.SEED_URLS)
    
    pages = crawler.run()
    print(f"\n📊 Crawled {pages} pages")
    
    # Show statistics
    stats = db.get_crawl_statistics()
    print(f"📊 Statistics: {stats}")
    
    # Cleanup
    test_db.unlink()
    print("✅ Crawler test completed")
