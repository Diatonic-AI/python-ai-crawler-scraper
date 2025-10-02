#!/usr/bin/env python3
"""
Content processor for extracting clean content from HTML,
converting to Markdown, and discovering links.
"""

import re
import hashlib
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urljoin, urlparse
from slugify import slugify


class ContentProcessor:
    """Processes HTML content into clean Markdown with metadata."""
    
    @staticmethod
    def remove_boilerplate(soup: BeautifulSoup) -> BeautifulSoup:
        """
        Remove common boilerplate elements from HTML.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            Cleaned BeautifulSoup object
        """
        # Remove script and style tags
        for tag in soup(['script', 'style', 'noscript', 'iframe']):
            tag.decompose()
        
        # Remove common boilerplate elements
        for selector in [
            'nav', 'header', 'footer', 'aside',
            '.navigation', '.nav', '.menu',
            '.sidebar', '.footer', '.header',
            '.advertisement', '.ad', '.ads',
            '.social-media', '.share-buttons',
            '.comments', '.related-posts'
        ]:
            for element in soup.select(selector):
                element.decompose()
        
        return soup
    
    @staticmethod
    def extract_title(soup: BeautifulSoup, url: str) -> str:
        """Extract page title from HTML."""
        # Try various title sources
        title = None
        
        # 1. <title> tag
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        
        # 2. h1 tag
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text().strip()
        
        # 3. og:title meta tag
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content'].strip()
        
        # 4. Fallback to URL path
        if not title:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/').split('/')[-1]
            title = path.replace('-', ' ').replace('_', ' ').title() or 'Untitled'
        
        return title
    
    @staticmethod
    def extract_content(html: str, url: str) -> Dict:
        """
        Extract clean content from HTML.
        
        Args:
            html: Raw HTML content
            url: Source URL
        
        Returns:
            Dict with extracted data
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract title
        title = ContentProcessor.extract_title(soup, url)
        
        # Remove boilerplate
        soup = ContentProcessor.remove_boilerplate(soup)
        
        # Find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|article|post', re.I)) or soup.body
        
        if not main_content:
            main_content = soup
        
        # Extract text content
        text_content = main_content.get_text(separator='\n', strip=True)
        
        # Clean up excessive whitespace
        text_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', text_content)
        
        # Convert to Markdown
        markdown_content = md(
            str(main_content),
            heading_style="ATX",
            bullets="-",
            code_language="python",
            strip=['script', 'style']
        )
        
        # Clean markdown
        markdown_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', markdown_content).strip()
        
        # Extract links
        links = ContentProcessor.extract_links(soup, url)
        
        # Calculate word count
        word_count = len(text_content.split())
        
        # Generate checksum
        checksum = hashlib.sha256(markdown_content.encode()).hexdigest()[:16]
        
        # Generate slug with URL hash to ensure uniqueness
        slug = slugify(title)
        # Add URL hash suffix to prevent collisions
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
        slug = f"{slug}-{url_hash}"
        
        return {
            'title': title,
            'slug': slug,
            'content': text_content,
            'markdown_content': markdown_content,
            'word_count': word_count,
            'checksum': checksum,
            'links': links
        }
    
    @staticmethod
    def extract_links(soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        Extract and categorize links from HTML.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
        
        Returns:
            List of link dictionaries
        """
        links = []
        base_domain = urlparse(base_url).netloc
        
        for link_tag in soup.find_all('a', href=True):
            href = link_tag.get('href', '').strip()
            
            if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            link_domain = urlparse(absolute_url).netloc
            
            # Determine link type
            link_type = 'internal' if link_domain == base_domain else 'external'
            
            # Extract anchor text
            anchor_text = link_tag.get_text(strip=True)
            
            links.append({
                'target_url': absolute_url,
                'link_type': link_type,
                'anchor_text': anchor_text
            })
        
        return links
    
    @staticmethod
    def create_wiki_links(markdown: str, internal_links: List[str], url_to_title: Dict[str, str]) -> str:
        """
        Replace internal links with Obsidian-style wiki-links.
        
        Args:
            markdown: Markdown content
            internal_links: List of internal URLs
            url_to_title: Mapping of URLs to page titles
        
        Returns:
            Markdown with wiki-links
        """
        for url in internal_links:
            title = url_to_title.get(url)
            if title:
                # Find markdown links to this URL
                pattern = rf'\[([^\]]+)\]\({re.escape(url)}\)'
                replacement = rf'[[{title}]]'
                markdown = re.sub(pattern, replacement, markdown)
        
        return markdown


if __name__ == "__main__":
    # Test content processor
    test_html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <header><nav>Navigation</nav></header>
            <main>
                <h1>Main Heading</h1>
                <p>This is the main content.</p>
                <a href="/internal">Internal Link</a>
                <a href="https://external.com">External Link</a>
            </main>
            <footer>Footer content</footer>
        </body>
    </html>
    """
    
    result = ContentProcessor.extract_content(test_html, "https://example.com/test")
    
    print(f"Title: {result['title']}")
    print(f"Slug: {result['slug']}")
    print(f"Word Count: {result['word_count']}")
    print(f"Links: {len(result['links'])}")
    print(f"Checksum: {result['checksum']}")
    print(f"\nMarkdown Preview:\n{result['markdown_content'][:200]}...")
