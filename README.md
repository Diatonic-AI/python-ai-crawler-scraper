# AI-Powered Web Crawler & Scraper

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent web crawler that uses LLM (Large Language Models) to enhance content extraction, normalize titles, extract tags, and generate Obsidian-compatible markdown vaults.

## 🌟 Features

### Core Crawling
- **Smart URL Management**: BFS-based crawling with depth control and domain filtering
- **Robust Error Handling**: Automatic retries with exponential backoff
- **Rate Limiting**: Configurable request delays to respect server resources
- **Content Filtering**: Skip binary files, media, and non-content paths

### Enhanced Database (New!)
- **Priority-Based Frontier Queue**: Intelligent URL prioritization for efficient crawling
- **Entity Extraction Storage**: Track people, organizations, locations, and concepts
- **LLM Operation Logging**: Monitor token usage, performance, and success rates
- **PageRank Computation**: Identify important pages based on link analysis
- **Crawl Job Tracking**: Session management with comprehensive statistics

### LLM-Powered Processing
- **Title Normalization**: Improve page titles using AI
- **Tag Extraction**: Automatic tagging based on content analysis
- **Entity Recognition**: Extract named entities from pages
- **Content Summarization**: Generate concise summaries

### Obsidian Vault Generation
- **Wiki-style Links**: Automatic internal linking between pages
- **Frontmatter Metadata**: Title, URL, tags, timestamps, word count
- **Backlink Support**: Track which pages link to each document
- **Clean Markdown**: Properly formatted content with preserved structure

## 📋 Requirements

- Python 3.8+
- SQLite 3
- Ollama (for LLM features) or compatible API endpoint
- Required Python packages (see `requirements.txt`)

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/DiatomicAI/python-ai-crawler-scraper.git
cd python-ai-crawler-scraper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Run a test crawl
python main.py --seeds https://docs.python.org/3/tutorial/ --max-pages 10 --max-depth 2
```

## 💻 Usage Examples

### Basic Crawl
```bash
python main.py --seeds https://example.com --max-pages 50 --max-depth 2
```

### Crawl Without LLM (Faster)
```bash
python main.py --seeds https://example.com --skip-llm --max-pages 100
```

### Resume Previous Crawl
```bash
python main.py --resume
```

### Multiple Seeds
```bash
python main.py --seeds https://site1.com https://site2.com --max-pages 100
```

## 📊 Test Results

Real-world crawl on Python documentation:
```
✅ Crawled 10 pages successfully
📊 Extracted 615 links (580 internal, 35 external)  
📄 Generated 10 Obsidian markdown files
💾 Database: 3.2MB with full content and metadata
```

## 🗄️ Database Schema

### Enhanced Tables
- `pages` - Crawled pages with content and metadata
- `links` - Page relationships (src → dst)
- `entities` - Extracted named entities
- `frontier` - Priority queue for URL crawling
- `crawl_jobs` - Session tracking
- `llm_operations_log` - LLM usage metrics
- `fetch_log` - HTTP request history

## 📁 Project Structure

```
python-ai-crawler-scraper/
├── main.py                   # Main orchestration
├── crawler.py                # Core crawler engine
├── database_enhanced.py      # Enhanced database with frontier
├── llm_normalizer.py        # LLM integration
├── content_processor.py     # HTML to Markdown
├── obsidian_writer.py       # Vault generation
├── test_enhanced_crawler.py # Test suite
└── requirements.txt         # Dependencies
```

## 🔧 Configuration

Edit `.env`:

```ini
# Crawl Settings
SEED_URLS=https://example.com
MAX_DEPTH=2
MAX_PAGES=100
REQUEST_DELAY=1.0

# LLM Settings
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_enhanced_crawler.py
```

Tests include:
- ✅ Frontier queue operations
- ✅ Entity extraction and storage
- ✅ LLM operation logging
- ✅ PageRank computation
- ✅ Enhanced statistics

## 🤝 Contributing

Contributions welcome! Please fork and submit PRs.

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

Built with BeautifulSoup4, Requests, Ollama, and inspired by Obsidian.

---

**Diatonic AI** | [@DiatomicAI](https://github.com/DiatomicAI)
