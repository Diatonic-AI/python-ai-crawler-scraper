# 🏗️ Enhanced LLM-Orchestrated Web Crawler Architecture

## 🎯 Vision & Goals

Transform the basic web crawler into a comprehensive, LLM-orchestrated system that:

1. **Auto-discovers** public entry points and continuously expands coverage
2. **Crawls respectfully** with robots.txt, rate limiting, and politeness policies
3. **Normalizes content** to Obsidian-ready Markdown with rich metadata
4. **Uses LLM intelligence** to plan, prioritize, classify, extract, and summarize
5. **Builds knowledge graphs** with backlinks, entities, and semantic relationships
6. **Provides dashboards** for monitoring progress, quality, and coverage
7. **Maintains ethics** with PII filtering, opt-out registry, and audit logs

---

## 🌍 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│         Schedules crawl waves, enforces budgets, manages scope  │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ├──► 🤖 LLM PLANNER (Scope & Policy Generator)
          │    Input: Seeds, sitemaps, region catalogs
          │    Output: Crawl policy JSON (depth, URL patterns, budgets)
          │
          ├──► 📥 FETCHER (HTTP GET with politeness)
          │    ├─ robots.txt compliance
          │    ├─ ETag/Last-Modified caching
          │    ├─ Rate limiting per host
          │    ├─ Retries with exponential backoff
          │    └─ Circuit breakers
          │
          ├──► 📝 PARSER (Boilerplate removal & content extraction)
          │    ├─ BeautifulSoup for HTML parsing
          │    ├─ Trafilatura for main content
          │    ├─ markdownify for Markdown conversion
          │    └─ Link & asset discovery
          │
          ├──► 🤖 LLM NORMALIZER (Content cleanup & summarization)
          │    Input: Raw Markdown, title, content preview
          │    Output: Enhanced title, clean Markdown, abstractive summary
          │
          ├──► 🤖 LLM CLASSIFIER (Page type & entity extraction)
          │    Input: Title, content, metadata
          │    Output: Page type (docs/blog/product), language, entities
          │
          ├──► 🤖 LLM PRIORITIZER (Frontier scoring)
          │    Input: Frontier URLs with metadata
          │    Output: Priority scores (0-1) for each URL
          │
          ├──► 🔗 GRAPH BUILDER (Backlinks & metrics)
          │    ├─ Create/update pages and links
          │    ├─ Compute backlinks
          │    ├─ PageRank calculation
          │    └─ Entity relationships
          │
          ├──► 💾 PERSISTER (Obsidian vault & SQLite)
          │    ├─ Obsidian .md files with YAML frontmatter
          │    ├─ Deterministic slugs
          │    ├─ Idempotent upserts
          │    └─ Change detection (checksums)
          │
          └──► 📊 MONITORING & DASHBOARD
               ├─ Streamlit dashboard (crawl status, graphs, coverage)
               ├─ Audit logs (all LLM calls, fetch operations)
               ├─ Error tracking & alerting
               └─ Budget monitoring (tokens, requests, time)
```

---

## 📦 Enhanced Database Schema

### Tables Added/Enhanced

#### **1. pages** (Enhanced)
```sql
CREATE TABLE pages (
    url TEXT PRIMARY KEY,
    title TEXT,
    slug TEXT UNIQUE,
    md_path TEXT,
    site TEXT,                -- Domain/site identifier
    content_hash TEXT,        -- SHA256 for change detection
    word_count INTEGER,
    depth INTEGER,
    first_seen TEXT,          -- ISO timestamp
    last_seen TEXT,           -- ISO timestamp
    status TEXT,              -- pending, crawled, processed, written
    type TEXT,                -- docs, blog, product, api (from LLM)
    summary TEXT,             -- Abstractive summary (from LLM)
    lang TEXT DEFAULT 'en',
    content TEXT,
    markdown_content TEXT,
    metadata TEXT,            -- JSON blob
    created_at TEXT,
    updated_at TEXT
);
```

#### **2. frontier** (NEW - Priority Queue)
```sql
CREATE TABLE frontier (
    url TEXT PRIMARY KEY,
    score REAL DEFAULT 0.5,     -- 0-1, higher = more important (from LLM)
    next_due_at TEXT,           -- When to recrawl
    reason TEXT,                -- Why this URL is in frontier
    domain_budget_left INTEGER, -- Per-domain quota
    crawl_policy_json TEXT,     -- JSON crawl rules
    discovered_at TEXT,
    priority INTEGER DEFAULT 50,-- 0-100
    attempts INTEGER DEFAULT 0,
    last_attempt_at TEXT,
    created_at TEXT
);
```

#### **3. entities** (NEW - LLM Extraction)
```sql
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    page_url TEXT,
    kind TEXT,            -- person, organization, product, concept
    label TEXT,
    value_json TEXT,      -- JSON properties
    confidence REAL,      -- 0-1
    created_at TEXT,
    FOREIGN KEY (page_url) REFERENCES pages(url)
);
```

#### **4. llm_operations_log** (NEW - Audit Trail)
```sql
CREATE TABLE llm_operations_log (
    id INTEGER PRIMARY KEY,
    operation_type TEXT,  -- planner, prioritizer, normalizer, classifier
    input_data TEXT,      -- JSON input
    output_data TEXT,     -- JSON output
    tokens_used INTEGER,
    duration_ms INTEGER,
    model TEXT,
    status TEXT,          -- success, failure
    error TEXT,
    created_at TEXT
);
```

#### **5. scope_registry** (NEW - Domain Rules)
```sql
CREATE TABLE scope_registry (
    id INTEGER PRIMARY KEY,
    domain TEXT UNIQUE,
    allowed BOOLEAN,
    max_depth INTEGER,
    max_pages INTEGER,
    request_delay REAL,
    rules_json TEXT,      -- Per-domain crawl rules
    created_at TEXT,
    updated_at TEXT
);
```

#### **6. crawl_jobs** (NEW - Job Tracking)
```sql
CREATE TABLE crawl_jobs (
    id INTEGER PRIMARY KEY,
    seed TEXT,
    scope_id INTEGER,
    started_at TEXT,
    finished_at TEXT,
    stats_json TEXT,
    status TEXT,          -- running, completed, failed
    created_at TEXT
);
```

---

## 🤖 LLM Orchestration Modules

### 1. **Scope Planner** (LLM-Assisted)

**Purpose**: Generate crawl policy from seeds and site hints

**Input**:
```json
{
  "seeds": ["https://example.com", "https://docs.example.com"],
  "site_hints": {
    "allowed_domains": ["example.com"],
    "region": "us-west-2",
    "type": "documentation"
  }
}
```

**LLM Prompt**:
```
You are a web crawl policy generator. Given seed URLs and hints, 
create a JSON crawl policy with:
- max_depth (1-5)
- max_pages (10-10000)
- URL patterns (regex for inclusion/exclusion)
- request_delay (0.5-5.0 seconds)
- blacklist/whitelist patterns

Output ONLY valid JSON.
```

**Output**:
```json
{
  "max_depth": 3,
  "max_pages": 500,
  "url_patterns": {
    "include": ["^https://example\\.com/docs/.*"],
    "exclude": [".*/api/.*", ".*/admin/.*"]
  },
  "request_delay": 1.0,
  "per_domain_quota": 100
}
```

---

### 2. **URL Prioritizer** (LLM-Assisted)

**Purpose**: Score frontier URLs for crawl priority

**Input**:
```json
{
  "urls": [
    {
      "url": "https://example.com/docs/getting-started",
      "discovered_from": "https://example.com/docs",
      "anchor_text": "Getting Started Guide",
      "depth": 2,
      "site_type": "docs"
    }
  ]
}
```

**LLM Prompt**:
```
You are a URL prioritizer. Score each URL (0-1) based on:
- Novelty (is it likely to have unique content?)
- Authority (is it linked from important pages?)
- Freshness (is it likely to change frequently?)
- Relevance (does it match crawl goals?)

Output ONLY a JSON array with url and score.
```

**Output**:
```json
{
  "scores": [
    {"url": "https://example.com/docs/getting-started", "score": 0.92}
  ]
}
```

---

### 3. **Content Normalizer** (LLM-Assisted)

**Purpose**: Clean and enhance content with summaries

**Input**:
```json
{
  "title": "Getting Started - Example Docs",
  "markdown_snippet": "# Installation\nRun: npm install example...",
  "word_count": 542
}
```

**LLM Prompt**:
```
You are a content normalizer. Given a title and Markdown snippet:
1. Improve the title (max 80 chars, clear and descriptive)
2. Generate 3-7 relevant tags (lowercase)
3. Create a 1-2 sentence abstractive summary

Output ONLY valid JSON with keys: title, tags, summary
```

**Output**:
```json
{
  "title": "Example Installation and Setup Guide",
  "tags": ["installation", "setup", "npm", "getting-started", "documentation"],
  "summary": "Step-by-step guide for installing the Example library using npm. Covers prerequisites, installation commands, and initial configuration."
}
```

---

### 4. **Classifier / Extractor** (LLM-Assisted)

**Purpose**: Classify page type and extract entities

**Input**:
```json
{
  "title": "Amazon S3 - Simple Storage Service",
  "content_sample": "Amazon S3 is an object storage service...",
  "metadata": {"keywords": ["storage", "cloud", "aws"]}
}
```

**LLM Prompt**:
```
You are a page classifier and entity extractor. Analyze the content and output:
- type: One of [docs, blog, product, api, tutorial, reference, guide, faq]
- lang: ISO 639-1 language code
- entities: Array of {kind, label, description}
  - kind: person, organization, product, concept, location

Output ONLY valid JSON.
```

**Output**:
```json
{
  "type": "product",
  "lang": "en",
  "entities": [
    {
      "kind": "product",
      "label": "Amazon S3",
      "description": "Object storage service by AWS"
    },
    {
      "kind": "organization",
      "label": "AWS",
      "description": "Amazon Web Services"
    },
    {
      "kind": "concept",
      "label": "Object Storage",
      "description": "Storage architecture for unstructured data"
    }
  ]
}
```

---

## 🔄 Crawl Workflow

### Phase 1: **Initialization**

1. Load seeds from config/CLI
2. LLM **Planner** generates crawl policy
3. Add seeds to **frontier** with high priority
4. Initialize **crawl job** in database

### Phase 2: **Discovery Loop**

```python
while frontier.has_urls() and not over_budget():
    # Get batch of highest priority URLs
    batch = frontier.get_batch(limit=10, min_score=0.5)
    
    for url_record in batch:
        # 1. Fetch HTML
        response = fetcher.fetch(url_record.url, policy=url_record.crawl_policy)
        
        if not response.ok:
            log_fetch_error(url, response.status_code)
            continue
        
        # 2. Parse content
        parsed = parser.extract_content(response.html, url)
        
        # 3. LLM Normalizer (enhance title, generate summary)
        normalized = llm_normalizer.process(
            title=parsed.title,
            markdown=parsed.markdown,
            content_sample=parsed.content[:1000]
        )
        
        # 4. LLM Classifier (page type, entities)
        classified = llm_classifier.classify(
            title=normalized.title,
            content=parsed.content,
            metadata=parsed.metadata
        )
        
        # 5. Store page
        db.upsert_page_enhanced(url, {
            'title': normalized.title,
            'slug': generate_slug(normalized.title),
            'content': parsed.content,
            'markdown_content': parsed.markdown,
            'type': classified.type,
            'summary': normalized.summary,
            'lang': classified.lang,
            'content_hash': hash_content(parsed.content),
            'word_count': len(parsed.content.split()),
            'depth': url_record.depth,
            'status': 'processed'
        })
        
        # 6. Extract and store entities
        for entity in classified.entities:
            db.add_entity(
                page_url=url,
                kind=entity.kind,
                label=entity.label,
                value_data={'description': entity.description},
                confidence=0.9
            )
        
        # 7. Discover new links
        new_links = parsed.links
        filtered_links = [link for link in new_links if should_crawl(link)]
        
        # 8. LLM Prioritizer scores new URLs
        scored_links = llm_prioritizer.score_batch(filtered_links)
        
        # 9. Add to frontier
        for link_record in scored_links:
            db.add_to_frontier(
                url=link_record.url,
                score=link_record.score,
                reason="Discovered from " + url,
                policy=url_record.crawl_policy,
                priority=int(link_record.score * 100)
            )
        
        # 10. Remove from frontier
        db.remove_from_frontier(url)
```

### Phase 3: **Graph Building**

1. Compute backlinks for all pages
2. Calculate PageRank scores
3. Build entity relationship graph
4. Update page metadata with graph metrics

### Phase 4: **Vault Writing**

1. For each processed page:
   - Generate Obsidian-compatible Markdown
   - Add YAML frontmatter with metadata
   - Convert internal links to `[[wiki-links]]`
   - Add backlinks section
   - Write to vault directory

2. Generate index files:
   - `INDEX.md`: Table of contents
   - `GRAPH.md`: Visual graph representation
   - `ENTITIES.md`: Entity index

---

## 📊 Obsidian Markdown Contract

### Deterministic Slugs

```python
def generate_slug(title: str, url: str) -> str:
    # 1. Clean title
    clean = title.lower().strip()
    clean = re.sub(r'[^a-z0-9\s-]', '', clean)
    clean = re.sub(r'\s+', '-', clean)
    
    # 2. Add URL hash for uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    
    return f"{clean}-{url_hash}"
```

### YAML Frontmatter (Ordered)

```yaml
---
title: "Example Installation and Setup Guide"
source_url: "https://example.com/docs/getting-started"
slug: "example-installation-and-setup-guide-a1b2c3d4"
created: "2025-10-02T08:30:00Z"
last_crawled: "2025-10-02T08:30:00Z"
tags: [installation, setup, npm, documentation]
aliases: ["Getting Started", "Setup Guide"]
word_count: 542
outbound_links: 15
backlinks: []
checksum_sha256: "abc123..."
crawl_depth: 2
page_type: "docs"
lang: "en"
summary: "Step-by-step guide for installing the Example library using npm."
entities:
  - kind: "product"
    label: "Example Library"
  - kind: "concept"
    label: "NPM"
---

# Example Installation and Setup Guide

[Content follows...]

## Backlinks

- [[Home Page]] via "Getting Started"
- [[Documentation Index]] via "Installation"

## Metadata

- Site: example.com
- Type: Documentation
- PageRank: 0.042
- External Links: 3
```

---

## 🛡️ Ethical & Legal Guardrails

### 1. **robots.txt Compliance**

```python
def check_robots_txt(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    
    return rp.can_fetch(USER_AGENT, url)
```

### 2. **Rate Limiting**

- Per-host rate limits (default: 1 request/second)
- Respect `Crawl-delay` from robots.txt
- Exponential backoff on errors
- Circuit breakers for unreliable hosts

### 3. **PII Filtering**

```python
def redact_pii(content: str) -> str:
    # Email addresses (unless @example.com, etc.)
    content = re.sub(r'\b[A-Za-z0-9._%+-]+@(?!example\.com)\w+\.\w+\b', '[EMAIL REDACTED]', content)
    
    # Phone numbers
    content = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE REDACTED]', content)
    
    # SSN patterns
    content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]', content)
    
    return content
```

### 4. **Opt-Out Registry**

```python
# Maintain opt-out list
opt_out_domains = load_opt_out_list()

def should_crawl(url: str) -> bool:
    domain = extract_domain(url)
    
    if domain in opt_out_domains:
        log_opt_out(url, domain)
        return False
    
    return True
```

### 5. **Audit Logging**

- Log every fetch (URL, timestamp, status, duration)
- Log every LLM call (operation, input/output, tokens, duration)
- Generate daily audit reports
- Retain logs for 90 days

---

## 📈 Monitoring & Dashboards

### Streamlit Dashboard (Planned)

**1. Overview Tab**
- Total pages crawled
- Coverage by domain
- Frontier size
- Current crawl rate
- LLM token usage

**2. Quality Tab**
- Pages with summaries
- Entity extraction stats
- Backlink coverage
- PageRank distribution

**3. Errors Tab**
- HTTP errors by code
- LLM failures
- Parsing errors
- Circuit breaker status

**4. Graph Tab**
- Interactive link graph
- Top pages by PageRank
- Entity relationships
- Orphaned pages

**5. Budget Tab**
- Token usage (by operation type)
- Request budget (by domain)
- Time budget (crawl duration)
- Cost estimates

---

## 📦 Package Requirements

```txt
# Core crawling
requests==2.31.0
httpx==0.27.0
beautifulsoup4==4.12.0
lxml==5.1.0
trafilatura==1.11.0
markdownify==0.12.0

# LLM orchestration
langchain==0.2.0
langchain-community==0.2.0
langchain-ollama==0.1.0
pydantic==2.8.0

# URL handling
tldextract==5.1.0
urlextract==1.9.0
url-normalize==1.4.0
robotexclusionrulesparser==1.7.1

# Database & caching
sqlite3 (stdlib)
sqlalchemy==2.0.0
requests-cache==1.2.0

# Reliability
tenacity==8.5.0

# Monitoring
streamlit==1.36.0
plotly==5.22.0
pandas==2.2.0

# Testing
pytest==8.2.0
pytest-httpserver==1.0.0
vcrpy==6.0.0
```

---

## 🚀 Quick Start (Enhanced System)

### 1. Install Dependencies

```bash
cd ~/dev/python-llama-demo/python-ai-crawler-scraper
source ../venv/bin/activate
pip install -r requirements_enhanced.txt
```

### 2. Configure

```bash
cp .env.example .env.enhanced
nano .env.enhanced
```

```env
# Seeds
SEED_URLS=https://example.com,https://docs.example.com

# LLM Settings
OLLAMA_BASE_URL=http://10.0.228.180:31134
LLM_MODEL=llama3.1:8b

# Budgets
MAX_PAGES=1000
MAX_DEPTH=4
MAX_TOKENS_PER_DAY=100000
REQUEST_DELAY=1.0

# Orchestration
ENABLE_LLM_PLANNER=true
ENABLE_LLM_PRIORITIZER=true
ENABLE_LLM_CLASSIFIER=true
ENABLE_ENTITY_EXTRACTION=true

# Monitoring
ENABLE_DASHBOARD=true
DASHBOARD_PORT=8501
```

### 3. Run Enhanced Crawler

```bash
python main_orchestrated.py \
  --seeds https://example.com \
  --max-pages 100 \
  --enable-dashboard
```

### 4. View Dashboard

Open browser to: `http://localhost:8501`

---

## 🔮 Future Enhancements

### Short-term (Next 2 weeks)
- [ ] Complete LLM orchestration modules
- [ ] Implement respectful fetcher with robots.txt
- [ ] Build Streamlit dashboard
- [ ] Add comprehensive testing

### Medium-term (Next month)
- [ ] Sitemap.xml discovery and parsing
- [ ] RSS/Atom feed integration
- [ ] Semantic search with vector embeddings
- [ ] Export to Neo4j for graph analysis

### Long-term (Next quarter)
- [ ] Distributed crawling support
- [ ] Real-time change detection
- [ ] ML-based duplicate detection
- [ ] Custom extraction rules per domain

---

**Built with**: Python 3.12 • LangChain • Ollama • BeautifulSoup • SQLite • Streamlit
