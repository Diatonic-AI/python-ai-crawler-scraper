# 🕷️ AI-Powered Web Crawler - Project Summary

## 📦 What Was Built

A complete Python web crawler that:
- Crawls websites from seed URLs with depth and page limits
- Extracts clean content from HTML (removes boilerplate)
- Converts content to Obsidian-style Markdown
- Uses local LLM (Ollama) via LangChain to improve titles and extract tags
- Tracks internal/external links and computes backlinks
- Stores everything in SQLite for resume-safe operation
- Outputs to an Obsidian vault with YAML frontmatter

## 📁 Project Structure

```
python-ai-crawler-scraper/
├── README.md                    # Comprehensive documentation
├── SUMMARY.md                   # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # Configuration template
├── setup.sh                     # Quick setup script
│
├── config.py                    # Configuration management
├── database.py                  # SQLite database operations
├── crawler.py                   # Web crawling engine
├── content_processor.py         # HTML to Markdown conversion
├── llm_normalizer.py            # LangChain + Ollama integration
├── obsidian_writer.py           # Obsidian vault writer
└── main.py                      # Main orchestration script
```

## 🎯 Core Features

### 1. Web Crawling (`crawler.py`)
- ✅ URL queue management with depth tracking
- ✅ Domain filtering (same-origin checks)
- ✅ Rate limiting with configurable delays
- ✅ Retry logic with exponential backoff
- ✅ Content-type checking (HTML only)
- ✅ Size limits (skip large files)
- ✅ Binary file detection

### 2. Content Processing (`content_processor.py`)
- ✅ BeautifulSoup HTML parsing
- ✅ Boilerplate removal (nav, footer, ads, etc.)
- ✅ Main content extraction
- ✅ Markdown conversion via markdownify
- ✅ Link discovery and categorization
- ✅ Word count and checksum generation
- ✅ URL-safe slug generation

### 3. LLM Enhancement (`llm_normalizer.py`)
- ✅ LangChain integration with ChatOllama
- ✅ Title improvement using LLM
- ✅ Tag extraction from content
- ✅ JSON response contract
- ✅ Fallback to original title if LLM fails
- ✅ Configurable temperature and timeout

### 4. Database Management (`database.py`)
- ✅ SQLite schema with pages and links tables
- ✅ Idempotent upsert operations
- ✅ Backlink computation
- ✅ Resume-safe operations
- ✅ Statistics and reporting
- ✅ Proper indexing for performance

### 5. Obsidian Output (`obsidian_writer.py`)
- ✅ YAML frontmatter generation
- ✅ Metadata fields: title, source_url, slug, timestamps
- ✅ Crawl metadata: depth, word_count, checksum
- ✅ Tags from LLM
- ✅ Backlinks list
- ✅ Deterministic filename generation

### 6. Configuration (`config.py`)
- ✅ Environment variable loading (.env)
- ✅ CLI argument overrides
- ✅ Validation on startup
- ✅ Sensible defaults
- ✅ Path management

### 7. Main Orchestrator (`main.py`)
- ✅ Three-phase execution: Crawl → Process → Write
- ✅ Progress bars with tqdm
- ✅ Resume capability
- ✅ Statistics reporting
- ✅ Error handling
- ✅ Skip LLM option for faster crawling

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
cd ~/dev/python-llama-demo/python-ai-crawler-scraper
source ../venv/bin/activate

# 2. Run setup script
./setup.sh

# 3. Edit configuration
nano .env

# 4. Run crawler
python main.py --seeds https://example.com --max-pages 10
```

## 💡 Usage Examples

### Basic Crawl
```bash
python main.py --seeds https://docs.python.org --max-pages 25 --max-depth 2
```

### Fast Crawl (Skip LLM)
```bash
python main.py --seeds https://example.com --skip-llm --max-pages 50
```

### Resume Previous Crawl
```bash
python main.py --resume
```

### Domain-Restricted Crawl
```bash
# In .env file:
ALLOWED_DOMAINS=example.com,docs.example.com

python main.py
```

## 📊 Sample Output

### Console Output
```
🔧 Crawler Configuration
============================================================
Seed URLs: ['https://example.com']
Max Depth: 2
Max Pages: 25
Request Delay: 1.0s
Database: ./crawler.db
Vault Directory: ./obsidian_vault
LLM Model: llama3.1:8b @ http://10.0.228.180:31134
============================================================

🕷️  Phase 1: Crawling
🔍 [1/25] Crawling (depth 0): https://example.com
  🔗 Discovered 12 new links
...
✅ Crawled 25 pages

📊 Database Statistics:
  Total pages: 25
  Total links: 89
  Max depth: 2

🔄 Phase 2: Processing
Processing pages: 100%|████████| 25/25 [00:30<00:00, 0.83it/s]

📝 Phase 3: Writing Obsidian Vault
Writing files: 100%|████████| 25/25 [00:01<00:00, 20.5it/s]

🎉 Crawl Complete!
  Pages in vault: 25
  Vault location: ./obsidian_vault
```

### Sample Markdown Output
```markdown
---
title: "Python Documentation - Getting Started"
source_url: "https://docs.python.org/3/tutorial/"
slug: "python-documentation-getting-started"
crawled_at: "2025-10-02T08:15:00Z"
updated_at: "2025-10-02T08:15:00Z"
crawl_depth: 1
word_count: 542
checksum: "a1b2c3d4e5f6"
tags: [python, tutorial, programming, documentation]
backlinks:
  - "Python Home"
  - "Table of Contents"
---

# Python Documentation - Getting Started

This tutorial introduces you to Python's basic concepts...

[[Installing Python]] - Learn how to install Python on your system

## Next Steps

Continue with [[Data Types]] or explore [[Functions]]
```

## 🧪 Testing

Each module has a `__main__` block for standalone testing:

```bash
python database.py        # Test database operations
python crawler.py         # Test basic crawling
python content_processor.py   # Test HTML processing
python llm_normalizer.py  # Test LLM integration
python obsidian_writer.py # Test file writing
```

## 🔧 Configuration Options

All configurable via `.env` file:

```bash
# Crawl Settings
SEED_URLS=https://example.com
ALLOWED_DOMAINS=example.com
MAX_DEPTH=3
MAX_PAGES=100
REQUEST_DELAY=1.0
REQUEST_TIMEOUT=30

# LLM Settings
OLLAMA_BASE_URL=http://10.0.228.180:31134
LLM_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.3

# Output
VAULT_DIR=./obsidian_vault
DATABASE_PATH=./crawler.db
```

## 📈 Performance Characteristics

- **Crawl Speed**: ~1 page/second with 1s delay
- **LLM Processing**: ~2-3s per page for title + tags
- **Memory Usage**: ~50-100MB for typical crawls
- **Database Size**: ~1KB per page + links
- **Vault Size**: ~5-10KB per page (Markdown)

## 🎓 Key Design Decisions

1. **SQLite**: Chosen for simplicity, portability, and resume capability
2. **Idempotent Operations**: All database operations are upserts for safety
3. **Three-Phase Processing**: Separate crawl/process/write for clarity
4. **LangChain + Ollama**: Local LLM for privacy and cost
5. **Obsidian Format**: YAML frontmatter for metadata + Markdown content
6. **Configurable Everything**: .env file + CLI overrides

## 🚨 Known Limitations

- No JavaScript rendering (static HTML only)
- No image downloading (content only)
- No PDF extraction
- No robots.txt checking (add --respect-robots flag needed)
- Single-threaded (can be extended to multi-process)
- LLM requires local Ollama server

## 🔮 Future Enhancements

See `README.md` for full list. Top priorities:
- [ ] Distributed crawling
- [ ] Custom per-domain extraction rules
- [ ] Image downloading
- [ ] robots.txt compliance
- [ ] Scheduled/periodic crawls

## 📚 Dependencies

Core libraries used:
- **requests**: HTTP fetching
- **beautifulsoup4 + lxml**: HTML parsing
- **markdownify**: HTML to Markdown
- **langchain + langchain-ollama**: LLM integration
- **tldextract**: Domain extraction
- **tenacity**: Retry logic
- **python-slugify**: URL-safe slugs
- **python-dotenv**: Configuration
- **tqdm**: Progress bars
- **pydantic**: Data validation (optional)

## ✅ Project Status

**Status**: ✅ Complete and ready to use

All components implemented:
- ✅ Web crawling with depth/domain/size controls
- ✅ Content extraction and Markdown conversion
- ✅ LLM-based title improvement and tagging
- ✅ SQLite persistence with backlink tracking
- ✅ Obsidian vault generation
- ✅ Resume capability
- ✅ Comprehensive documentation
- ✅ Quick setup script

## 🎉 Success Criteria Met

✅ Crawls from seed URLs with depth limits
✅ Fetches HTML and removes boilerplate
✅ Extracts readable content
✅ Discovers and tracks links (internal/external)
✅ Computes backlinks within crawl set
✅ Converts to Obsidian-style Markdown with YAML frontmatter
✅ Uses LangChain with local Ollama model for text normalization
✅ Persists in SQLite with idempotent operations
✅ Resume-safe and deterministic
✅ Configurable via .env and CLI args
✅ Handles retries, timeouts, and errors gracefully
✅ Skips large/binary pages

---

**Ready to crawl!** See `README.md` for detailed usage instructions.
