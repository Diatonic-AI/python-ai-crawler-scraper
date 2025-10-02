#!/usr/bin/env python3
"""
SQLite database management for the web crawler.
Provides idempotent operations for resume-safe functionality.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from contextlib import contextmanager


class CrawlerDatabase:
    """Manages SQLite database for crawl data and link relationships."""
    
    def __init__(self, db_path: Path):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_db(self):
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Pages table: stores crawled page data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    slug TEXT UNIQUE,
                    content TEXT,
                    markdown_content TEXT,
                    word_count INTEGER DEFAULT 0,
                    crawl_depth INTEGER DEFAULT 0,
                    checksum TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    processed BOOLEAN DEFAULT 0,
                    written_to_vault BOOLEAN DEFAULT 0
                )
            """)
            
            # Links table: stores outbound links from pages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    source_url TEXT,
                    target_url TEXT,
                    link_type TEXT DEFAULT 'internal',
                    anchor_text TEXT,
                    created_at TEXT,
                    PRIMARY KEY (source_url, target_url),
                    FOREIGN KEY (source_url) REFERENCES pages(url) ON DELETE CASCADE
                )
            """)
            
            # Create indices for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_processed 
                ON pages(processed)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_depth 
                ON pages(crawl_depth)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_links_target 
                ON links(target_url)
            """)
            
            conn.commit()
            print(f"✅ Database initialized: {self.db_path}")
    
    def upsert_page(self, url: str, data: Dict) -> bool:
        """
        Insert or update a page record (idempotent operation).
        
        Args:
            url: Page URL (primary key)
            data: Dictionary with page data fields
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.utcnow().isoformat()
                
                # Serialize metadata to JSON if present
                metadata = json.dumps(data.get('metadata', {}))
                
                cursor.execute("""
                    INSERT INTO pages (
                        url, title, slug, content, markdown_content, 
                        word_count, crawl_depth, checksum, metadata, 
                        created_at, updated_at, processed, written_to_vault
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        title = excluded.title,
                        slug = excluded.slug,
                        content = excluded.content,
                        markdown_content = excluded.markdown_content,
                        word_count = excluded.word_count,
                        crawl_depth = excluded.crawl_depth,
                        checksum = excluded.checksum,
                        metadata = excluded.metadata,
                        updated_at = excluded.updated_at,
                        processed = excluded.processed,
                        written_to_vault = excluded.written_to_vault
                """, (
                    url,
                    data.get('title', ''),
                    data.get('slug', ''),
                    data.get('content', ''),
                    data.get('markdown_content', ''),
                    data.get('word_count', 0),
                    data.get('crawl_depth', 0),
                    data.get('checksum', ''),
                    metadata,
                    now,
                    now,
                    data.get('processed', False),
                    data.get('written_to_vault', False)
                ))
                
                conn.commit()
                return True
        
        except Exception as e:
            print(f"❌ Error upserting page {url}: {e}")
            return False
    
    def add_links(self, source_url: str, links: List[Dict]) -> int:
        """
        Add multiple links from a source page (idempotent).
        
        Args:
            source_url: Source page URL
            links: List of dicts with keys: target_url, link_type, anchor_text
        
        Returns:
            Number of links successfully added
        """
        added = 0
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                for link in links:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO links (
                                source_url, target_url, link_type, anchor_text, created_at
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            source_url,
                            link.get('target_url'),
                            link.get('link_type', 'internal'),
                            link.get('anchor_text', ''),
                            now
                        ))
                        added += cursor.rowcount
                    except Exception as e:
                        print(f"⚠️  Failed to add link {link.get('target_url')}: {e}")
                
                conn.commit()
        
        except Exception as e:
            print(f"❌ Error adding links from {source_url}: {e}")
        
        return added
    
    def get_page(self, url: str) -> Optional[Dict]:
        """Retrieve a page record by URL."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM pages WHERE url = ?", (url,))
                row = cursor.fetchone()
                
                if row:
                    data = dict(row)
                    # Deserialize metadata
                    if data.get('metadata'):
                        data['metadata'] = json.loads(data['metadata'])
                    return data
                
                return None
        
        except Exception as e:
            print(f"❌ Error retrieving page {url}: {e}")
            return None
    
    def get_unprocessed_pages(self, limit: int = 100) -> List[Dict]:
        """Get pages that haven't been processed yet."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM pages 
                    WHERE processed = 0 
                    ORDER BY crawl_depth ASC, created_at ASC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                pages = []
                
                for row in rows:
                    data = dict(row)
                    if data.get('metadata'):
                        data['metadata'] = json.loads(data['metadata'])
                    pages.append(data)
                
                return pages
        
        except Exception as e:
            print(f"❌ Error getting unprocessed pages: {e}")
            return []
    
    def mark_page_processed(self, url: str, written: bool = False):
        """Mark a page as processed and optionally written to vault."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE pages 
                    SET processed = 1, written_to_vault = ?, updated_at = ?
                    WHERE url = ?
                """, (written, datetime.utcnow().isoformat(), url))
                conn.commit()
        
        except Exception as e:
            print(f"❌ Error marking page processed {url}: {e}")
    
    def get_backlinks(self, target_url: str) -> List[Dict]:
        """Get all pages that link to a target URL."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT l.source_url, p.title, p.slug, l.anchor_text
                    FROM links l
                    LEFT JOIN pages p ON l.source_url = p.url
                    WHERE l.target_url = ?
                """, (target_url,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        
        except Exception as e:
            print(f"❌ Error getting backlinks for {target_url}: {e}")
            return []
    
    def get_outbound_links(self, source_url: str) -> List[Dict]:
        """Get all outbound links from a source URL."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT target_url, link_type, anchor_text
                    FROM links
                    WHERE source_url = ?
                """, (source_url,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        
        except Exception as e:
            print(f"❌ Error getting outbound links for {source_url}: {e}")
            return []
    
    def get_crawl_statistics(self) -> Dict:
        """Get overall crawl statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) as total FROM pages")
                total_pages = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as processed FROM pages WHERE processed = 1")
                processed_pages = cursor.fetchone()['processed']
                
                cursor.execute("SELECT COUNT(*) as written FROM pages WHERE written_to_vault = 1")
                written_pages = cursor.fetchone()['written']
                
                cursor.execute("SELECT COUNT(*) as total FROM links")
                total_links = cursor.fetchone()['total']
                
                cursor.execute("SELECT MAX(crawl_depth) as max_depth FROM pages")
                max_depth = cursor.fetchone()['max_depth'] or 0
                
                return {
                    'total_pages': total_pages,
                    'processed_pages': processed_pages,
                    'written_pages': written_pages,
                    'total_links': total_links,
                    'max_depth': max_depth,
                    'pending_pages': total_pages - processed_pages
                }
        
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {}
    
    def get_all_urls(self) -> Set[str]:
        """Get all URLs currently in the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT url FROM pages")
                rows = cursor.fetchall()
                return {row['url'] for row in rows}
        
        except Exception as e:
            print(f"❌ Error getting all URLs: {e}")
            return set()


if __name__ == "__main__":
    # Test database operations
    from pathlib import Path
    
    test_db = Path("test_crawler.db")
    db = CrawlerDatabase(test_db)
    
    # Test upsert
    test_data = {
        'title': 'Test Page',
        'slug': 'test-page',
        'content': 'This is test content',
        'crawl_depth': 1,
        'word_count': 4
    }
    
    db.upsert_page("https://example.com/test", test_data)
    
    # Test retrieval
    page = db.get_page("https://example.com/test")
    print(f"Retrieved page: {page['title']}")
    
    # Test statistics
    stats = db.get_crawl_statistics()
    print(f"Statistics: {stats}")
    
    # Cleanup
    test_db.unlink()
    print("✅ Database tests completed")
