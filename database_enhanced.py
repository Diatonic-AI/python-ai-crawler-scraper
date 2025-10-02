#!/usr/bin/env python3
"""
Enhanced SQLite database management for LLM-orchestrated web crawler.
Supports frontier management, entities, crawl jobs, and graph building.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from contextlib import contextmanager


class EnhancedCrawlerDatabase:
    """Enhanced database with frontier, entities, jobs, and graph support."""
    
    def __init__(self, db_path: Path):
        """Initialize database connection and create enhanced schema."""
        self.db_path = db_path
        self._init_enhanced_schema()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections with row factory."""
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
    
    def _init_enhanced_schema(self):
        """Create comprehensive database schema for orchestrated crawling."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # ==================== PAGES TABLE ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    slug TEXT UNIQUE,
                    md_path TEXT,
                    site TEXT,  -- Domain/site identifier
                    content_hash TEXT,  -- SHA256 of content for change detection
                    word_count INTEGER DEFAULT 0,
                    depth INTEGER DEFAULT 0,
                    first_seen TEXT,
                    last_seen TEXT,
                    status TEXT DEFAULT 'pending',  -- pending, crawled, processed, written
                    type TEXT,  -- docs, blog, product, api, etc.
                    summary TEXT,  -- Abstractive summary from LLM
                    lang TEXT DEFAULT 'en',
                    content TEXT,
                    markdown_content TEXT,
                    metadata TEXT,  -- JSON blob
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # ==================== LINKS TABLE ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    src_url TEXT,
                    dst_url TEXT,
                    rel TEXT DEFAULT 'internal',  -- internal, external
                    anchor_text TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    PRIMARY KEY (src_url, dst_url),
                    FOREIGN KEY (src_url) REFERENCES pages(url) ON DELETE CASCADE
                )
            """)
            
            # ==================== ASSETS TABLE ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_url TEXT,
                    path TEXT,
                    mime TEXT,
                    bytes INTEGER DEFAULT 0,
                    hash TEXT,
                    created_at TEXT,
                    FOREIGN KEY (page_url) REFERENCES pages(url) ON DELETE CASCADE
                )
            """)
            
            # ==================== CRAWL JOBS TABLE ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seed TEXT,
                    scope_id INTEGER,
                    started_at TEXT,
                    finished_at TEXT,
                    stats_json TEXT,  -- JSON statistics
                    status TEXT DEFAULT 'running',  -- running, completed, failed
                    created_at TEXT
                )
            """)
            
            # ==================== FETCH LOG TABLE ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fetch_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    ts TEXT,
                    http_status INTEGER,
                    bytes INTEGER DEFAULT 0,
                    duration_ms INTEGER DEFAULT 0,
                    error TEXT,
                    created_at TEXT
                )
            """)
            
            # ==================== ENTITIES TABLE (LLM Extraction) ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_url TEXT,
                    kind TEXT,  -- person, organization, product, concept, etc.
                    label TEXT,
                    value_json TEXT,  -- JSON properties
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT,
                    FOREIGN KEY (page_url) REFERENCES pages(url) ON DELETE CASCADE
                )
            """)
            
            # ==================== FRONTIER TABLE (Priority Queue) ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS frontier (
                    url TEXT PRIMARY KEY,
                    score REAL DEFAULT 0.5,  -- 0-1, higher = more important
                    next_due_at TEXT,
                    reason TEXT,  -- Why this URL is in frontier
                    domain_budget_left INTEGER DEFAULT 100,
                    crawl_policy_json TEXT,  -- JSON crawl policy
                    discovered_at TEXT,
                    priority INTEGER DEFAULT 50,  -- 0-100
                    attempts INTEGER DEFAULT 0,
                    last_attempt_at TEXT,
                    created_at TEXT
                )
            """)
            
            # ==================== SCOPE REGISTRY TABLE ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scope_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE,
                    allowed BOOLEAN DEFAULT 1,
                    max_depth INTEGER DEFAULT 3,
                    max_pages INTEGER DEFAULT 100,
                    request_delay REAL DEFAULT 1.0,
                    rules_json TEXT,  -- JSON crawl rules
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # ==================== LLM OPERATIONS LOG ====================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_operations_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT,  -- planner, prioritizer, normalizer, classifier, etc.
                    input_data TEXT,  -- JSON input
                    output_data TEXT,  -- JSON output
                    tokens_used INTEGER DEFAULT 0,
                    duration_ms INTEGER DEFAULT 0,
                    model TEXT,
                    status TEXT DEFAULT 'success',  -- success, failure
                    error TEXT,
                    created_at TEXT
                )
            """)
            
            # ==================== INDICES ====================
            # Pages indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_depth ON pages(depth)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_site ON pages(site)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_type ON pages(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_hash ON pages(content_hash)")
            
            # Links indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst_url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_rel ON links(rel)")
            
            # Frontier indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_frontier_score ON frontier(score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_frontier_priority ON frontier(priority DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_frontier_due ON frontier(next_due_at)")
            
            # Entities indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_kind ON entities(kind)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_label ON entities(label)")
            
            # Fetch log indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fetch_url ON fetch_log(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fetch_ts ON fetch_log(ts)")
            
            conn.commit()
            print(f"✅ Enhanced database initialized: {self.db_path}")
    
    # ==================== FRONTIER MANAGEMENT ====================
    
    def add_to_frontier(self, url: str, score: float, reason: str, 
                       policy: Dict = None, priority: int = 50) -> bool:
        """Add URL to frontier with priority scoring."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO frontier (
                        url, score, next_due_at, reason, 
                        crawl_policy_json, discovered_at, priority, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    url, score, now, reason,
                    json.dumps(policy or {}), now, priority, now
                ))
                
                return True
        except Exception as e:
            print(f"❌ Error adding to frontier {url}: {e}")
            return False
    
    def get_frontier_batch(self, limit: int = 100, 
                          min_score: float = 0.0) -> List[Dict]:
        """Get highest priority URLs from frontier."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM frontier 
                    WHERE score >= ? AND attempts < 3
                    ORDER BY priority DESC, score DESC, next_due_at ASC
                    LIMIT ?
                """, (min_score, limit))
                
                rows = cursor.fetchall()
                results = []
                
                for row in rows:
                    data = dict(row)
                    if data.get('crawl_policy_json'):
                        data['crawl_policy'] = json.loads(data['crawl_policy_json'])
                    results.append(data)
                
                return results
        except Exception as e:
            print(f"❌ Error getting frontier batch: {e}")
            return []
    
    def remove_from_frontier(self, url: str) -> bool:
        """Remove URL from frontier after successful crawl."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM frontier WHERE url = ?", (url,))
                return True
        except Exception as e:
            print(f"❌ Error removing from frontier {url}: {e}")
            return False
    
    def update_frontier_score(self, url: str, score: float) -> bool:
        """Update frontier URL score (from LLM prioritizer)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE frontier 
                    SET score = ?, updated_at = ?
                    WHERE url = ?
                """, (score, datetime.utcnow().isoformat(), url))
                return True
        except Exception as e:
            print(f"❌ Error updating frontier score {url}: {e}")
            return False
    
    # ==================== ENTITIES MANAGEMENT ====================
    
    def add_entity(self, page_url: str, kind: str, label: str, 
                  value_data: Dict, confidence: float = 1.0) -> int:
        """Add extracted entity from LLM."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                cursor.execute("""
                    INSERT INTO entities (
                        page_url, kind, label, value_json, confidence, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    page_url, kind, label, json.dumps(value_data), confidence, now
                ))
                
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ Error adding entity: {e}")
            return -1
    
    def get_entities_by_page(self, page_url: str) -> List[Dict]:
        """Get all entities extracted from a page."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM entities WHERE page_url = ?
                """, (page_url,))
                
                rows = cursor.fetchall()
                results = []
                
                for row in rows:
                    data = dict(row)
                    if data.get('value_json'):
                        data['value'] = json.loads(data['value_json'])
                    results.append(data)
                
                return results
        except Exception as e:
            print(f"❌ Error getting entities: {e}")
            return []
    
    def get_entities_by_kind(self, kind: str, limit: int = 100) -> List[Dict]:
        """Get entities by type (person, organization, etc.)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM entities 
                    WHERE kind = ?
                    ORDER BY confidence DESC
                    LIMIT ?
                """, (kind, limit))
                
                rows = cursor.fetchall()
                results = []
                
                for row in rows:
                    data = dict(row)
                    if data.get('value_json'):
                        data['value'] = json.loads(data['value_json'])
                    results.append(data)
                
                return results
        except Exception as e:
            print(f"❌ Error getting entities by kind: {e}")
            return []
    
    # ==================== LLM OPERATIONS LOGGING ====================
    
    def log_llm_operation(self, operation_type: str, input_data: Dict, 
                         output_data: Dict, tokens: int = 0, 
                         duration_ms: int = 0, model: str = "",
                         status: str = "success", error: str = None) -> int:
        """Log LLM operation for auditing and monitoring."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                cursor.execute("""
                    INSERT INTO llm_operations_log (
                        operation_type, input_data, output_data, tokens_used,
                        duration_ms, model, status, error, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    operation_type, json.dumps(input_data), json.dumps(output_data),
                    tokens, duration_ms, model, status, error, now
                ))
                
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ Error logging LLM operation: {e}")
            return -1
    
    def get_llm_operation_stats(self, operation_type: str = None) -> Dict:
        """Get statistics for LLM operations."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if operation_type:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_ops,
                            SUM(tokens_used) as total_tokens,
                            AVG(duration_ms) as avg_duration_ms,
                            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successful_ops,
                            SUM(CASE WHEN status='failure' THEN 1 ELSE 0 END) as failed_ops
                        FROM llm_operations_log
                        WHERE operation_type = ?
                    """, (operation_type,))
                else:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_ops,
                            SUM(tokens_used) as total_tokens,
                            AVG(duration_ms) as avg_duration_ms,
                            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successful_ops,
                            SUM(CASE WHEN status='failure' THEN 1 ELSE 0 END) as failed_ops
                        FROM llm_operations_log
                    """)
                
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            print(f"❌ Error getting LLM operation stats: {e}")
            return {}
    
    # ==================== CRAWL JOBS MANAGEMENT ====================
    
    def create_crawl_job(self, seed: str, scope_id: int = None) -> int:
        """Create new crawl job."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                cursor.execute("""
                    INSERT INTO crawl_jobs (
                        seed, scope_id, started_at, status, created_at
                    ) VALUES (?, ?, ?, 'running', ?)
                """, (seed, scope_id, now, now))
                
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ Error creating crawl job: {e}")
            return -1
    
    def update_crawl_job(self, job_id: int, stats: Dict, status: str = "completed") -> bool:
        """Update crawl job with statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                cursor.execute("""
                    UPDATE crawl_jobs 
                    SET finished_at = ?, stats_json = ?, status = ?
                    WHERE id = ?
                """, (now, json.dumps(stats), status, job_id))
                
                return True
        except Exception as e:
            print(f"❌ Error updating crawl job: {e}")
            return False
    
    # ==================== ENHANCED PAGE OPERATIONS ====================
    
    def upsert_page_enhanced(self, url: str, data: Dict) -> bool:
        """Enhanced page upsert with all new fields."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                # Serialize metadata
                metadata = json.dumps(data.get('metadata', {}))
                
                # Extract domain for site field
                from urllib.parse import urlparse
                parsed = urlparse(url)
                site = f"{parsed.netloc}"
                
                cursor.execute("""
                    INSERT INTO pages (
                        url, title, slug, md_path, site, content_hash, word_count,
                        depth, first_seen, last_seen, status, type, summary, lang,
                        content, markdown_content, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        title = excluded.title,
                        slug = excluded.slug,
                        md_path = excluded.md_path,
                        content_hash = excluded.content_hash,
                        word_count = excluded.word_count,
                        depth = excluded.depth,
                        last_seen = excluded.last_seen,
                        status = excluded.status,
                        type = excluded.type,
                        summary = excluded.summary,
                        lang = excluded.lang,
                        content = excluded.content,
                        markdown_content = excluded.markdown_content,
                        metadata = excluded.metadata,
                        updated_at = excluded.updated_at
                """, (
                    url,
                    data.get('title', ''),
                    data.get('slug', ''),
                    data.get('md_path', ''),
                    site,
                    data.get('content_hash', ''),
                    data.get('word_count', 0),
                    data.get('depth', 0),
                    now,  # first_seen
                    now,  # last_seen
                    data.get('status', 'pending'),
                    data.get('type', ''),
                    data.get('summary', ''),
                    data.get('lang', 'en'),
                    data.get('content', ''),
                    data.get('markdown_content', ''),
                    metadata,
                    now,  # created_at
                    now   # updated_at
                ))
                
                return True
        except Exception as e:
            print(f"❌ Error upserting enhanced page {url}: {e}")
            return False
    
    # ==================== GRAPH OPERATIONS ====================
    
    def compute_page_rank(self, damping: float = 0.85, max_iter: int = 100) -> Dict[str, float]:
        """Compute PageRank-like scores for all pages."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all pages
                cursor.execute("SELECT url FROM pages")
                urls = [row['url'] for row in cursor.fetchall()]
                
                if not urls:
                    return {}
                
                # Initialize PageRank
                num_pages = len(urls)
                page_rank = {url: 1.0 / num_pages for url in urls}
                
                # Build adjacency matrix
                cursor.execute("SELECT src_url, dst_url FROM links WHERE rel='internal'")
                links = cursor.fetchall()
                
                outbound_counts = {}
                inbound_links = {url: [] for url in urls}
                
                for link in links:
                    src = link['src_url']
                    dst = link['dst_url']
                    
                    if dst in inbound_links:
                        inbound_links[dst].append(src)
                    
                    outbound_counts[src] = outbound_counts.get(src, 0) + 1
                
                # Iterate PageRank
                for _ in range(max_iter):
                    new_rank = {}
                    
                    for url in urls:
                        rank_sum = 0.0
                        
                        for src in inbound_links[url]:
                            if src in page_rank and outbound_counts.get(src, 0) > 0:
                                rank_sum += page_rank[src] / outbound_counts[src]
                        
                        new_rank[url] = (1 - damping) / num_pages + damping * rank_sum
                    
                    page_rank = new_rank
                
                return page_rank
        except Exception as e:
            print(f"❌ Error computing PageRank: {e}")
            return {}
    
    def get_enhanced_statistics(self) -> Dict:
        """Get comprehensive statistics for the enhanced database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Pages stats
                cursor.execute("SELECT COUNT(*) as total FROM pages")
                stats['total_pages'] = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as count FROM pages WHERE status IN ('processed', 'written')")
                stats['processed_pages'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(DISTINCT site) as count FROM pages")
                stats['unique_sites'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(DISTINCT type) as count FROM pages WHERE type != ''")
                stats['unique_types'] = cursor.fetchone()['count']
                
                # Links stats
                cursor.execute("SELECT COUNT(*) as total FROM links")
                stats['total_links'] = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as count FROM links WHERE rel='internal'")
                stats['internal_links'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM links WHERE rel='external'")
                stats['external_links'] = cursor.fetchone()['count']
                
                # Entities stats
                cursor.execute("SELECT COUNT(*) as total FROM entities")
                stats['total_entities'] = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(DISTINCT kind) as count FROM entities")
                stats['unique_entity_kinds'] = cursor.fetchone()['count']
                
                # Frontier stats
                cursor.execute("SELECT COUNT(*) as total FROM frontier")
                stats['frontier_size'] = cursor.fetchone()['total']
                
                cursor.execute("SELECT AVG(score) as avg FROM frontier")
                avg_score = cursor.fetchone()['avg']
                stats['avg_frontier_score'] = round(avg_score, 3) if avg_score else 0.0
                
                # LLM stats
                llm_stats = self.get_llm_operation_stats()
                stats['llm_operations'] = llm_stats
                
                return stats
        except Exception as e:
            print(f"❌ Error getting enhanced statistics: {e}")
            return {}


    # ==================== COMPATIBILITY METHODS (for existing crawler) ====================
    
    def get_unprocessed_pages(self, limit: int = 100) -> List[Dict]:
        """Get pages that haven't been processed yet (compatibility method)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM pages 
                    WHERE status IN ('pending', 'crawled')
                    ORDER BY depth ASC, created_at ASC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                pages = []
                
                for row in rows:
                    data = dict(row)
                    if data.get('metadata'):
                        data['metadata'] = json.loads(data['metadata'])
                    # Map enhanced fields to old field names for compatibility
                    data['crawl_depth'] = data.get('depth', 0)
                    data['checksum'] = data.get('content_hash', '')
                    pages.append(data)
                
                return pages
        except Exception as e:
            print(f"❌ Error getting unprocessed pages: {e}")
            return []
    
    def get_all_urls(self) -> Set[str]:
        """Get all URLs currently in the database (compatibility method)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT url FROM pages")
                rows = cursor.fetchall()
                return {row['url'] for row in rows}
        except Exception as e:
            print(f"❌ Error getting all URLs: {e}")
            return set()
    
    def get_page(self, url: str) -> Optional[Dict]:
        """Retrieve a page record by URL (compatibility method)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM pages WHERE url = ?", (url,))
                row = cursor.fetchone()
                
                if row:
                    data = dict(row)
                    if data.get('metadata'):
                        data['metadata'] = json.loads(data['metadata'])
                    # Map enhanced fields to old field names
                    data['crawl_depth'] = data.get('depth', 0)
                    data['checksum'] = data.get('content_hash', '')
                    data['processed'] = data.get('status') == 'processed'
                    data['written_to_vault'] = data.get('status') == 'written'
                    return data
                
                return None
        except Exception as e:
            print(f"❌ Error retrieving page {url}: {e}")
            return None
    
    def add_links(self, source_url: str, links: List[Dict]) -> int:
        """Add multiple links from a source page (compatibility method)."""
        added = 0
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                for link in links:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO links (
                                src_url, dst_url, rel, anchor_text, first_seen, last_seen
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            source_url,
                            link.get('target_url'),
                            link.get('link_type', 'internal'),
                            link.get('anchor_text', ''),
                            now,
                            now
                        ))
                        added += cursor.rowcount
                    except Exception as e:
                        print(f"⚠️  Failed to add link {link.get('target_url')}: {e}")
                
                conn.commit()
        except Exception as e:
            print(f"❌ Error adding links from {source_url}: {e}")
        
        return added
    
    def get_backlinks(self, target_url: str) -> List[Dict]:
        """Get all pages that link to a target URL (compatibility method)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT l.src_url as source_url, p.title, p.slug, l.anchor_text
                    FROM links l
                    LEFT JOIN pages p ON l.src_url = p.url
                    WHERE l.dst_url = ?
                """, (target_url,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Error getting backlinks for {target_url}: {e}")
            return []
    
    def mark_page_processed(self, url: str, written: bool = False):
        """Mark a page as processed (compatibility method)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                status = 'written' if written else 'processed'
                cursor.execute("""
                    UPDATE pages 
                    SET status = ?, updated_at = ?
                    WHERE url = ?
                """, (status, datetime.utcnow().isoformat(), url))
                conn.commit()
        except Exception as e:
            print(f"❌ Error marking page processed {url}: {e}")
    
    def upsert_page(self, url: str, data: Dict) -> bool:
        """Compatibility wrapper for upsert_page_enhanced."""
        # Map old field names to enhanced schema
        enhanced_data = {
            'title': data.get('title', ''),
            'slug': data.get('slug', ''),
            'content': data.get('content', ''),
            'markdown_content': data.get('markdown_content', ''),
            'word_count': data.get('word_count', 0),
            'content_hash': data.get('checksum', ''),
            'depth': data.get('crawl_depth', 0),
            'metadata': data.get('metadata', {}),
            'status': 'processed' if data.get('processed') else 'pending'
        }
        return self.upsert_page_enhanced(url, enhanced_data)


if __name__ == "__main__":
    # Test enhanced database
    test_db = Path("test_enhanced.db")
    db = EnhancedCrawlerDatabase(test_db)
    
    # Test frontier
    db.add_to_frontier(
        "https://example.com/test",
        score=0.85,
        reason="High priority documentation",
        policy={"max_depth": 3, "request_delay": 1.0},
        priority=90
    )
    
    # Test entity
    db.add_entity(
        "https://example.com/test",
        kind="concept",
        label="Web Scraping",
        value_data={"description": "Automated web data extraction"},
        confidence=0.95
    )
    
    # Test LLM logging
    db.log_llm_operation(
        operation_type="planner",
        input_data={"seed": "https://example.com"},
        output_data={"max_depth": 3, "max_pages": 100},
        tokens=150,
        duration_ms=1200,
        model="llama3.1:8b"
    )
    
    # Get statistics
    stats = db.get_enhanced_statistics()
    print("📊 Enhanced Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Cleanup
    test_db.unlink()
    print("✅ Enhanced database tests completed")
