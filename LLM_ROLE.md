# 🤖 LLM Role in the Web Crawler

## The Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: CRAWLING                            │
│                    (NO LLM INVOLVED)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. WebCrawler (crawler.py)                                    │
│     └─> requests library                                       │
│         └─> Fetch HTML from URLs                               │
│         └─> Follow links                                       │
│         └─> Apply rate limiting                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 2: PROCESSING                           │
│              (LLM USED IN STEP 2.2 ONLY)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  2.1 ContentProcessor (content_processor.py)                   │
│      └─> BeautifulSoup: Parse HTML                             │
│      └─> Rule-based: Remove boilerplate                        │
│      └─> BeautifulSoup: Extract main content                   │
│      └─> markdownify: Convert to Markdown                      │
│      └─> Extract: Links, word count, checksum                  │
│      └─> slugify: Generate URL-safe slug                       │
│                                                                 │
│         ⬇ Extracted content passed to LLM                       │
│                                                                 │
│  2.2 LLMNormalizer (llm_normalizer.py) ⭐ LLM HERE             │
│      └─> LangChain + ChatOllama                                │
│          └─> Model: llama3.1:8b                                │
│          └─> Temperature: 0.3 (deterministic)                  │
│          └─> Two operations:                                   │
│              ├─> improve_title()                               │
│              │   Input:  "Example Domain"                      │
│              │   Output: "Use as Example Domain in Documents"  │
│              │                                                  │
│              └─> extract_tags()                                │
│                  Input:  Title + Content (first 1000 chars)    │
│                  Output: [example, domain, illustration, ...]  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 3: OUTPUT                               │
│                   (NO LLM INVOLVED)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  3. ObsidianWriter (obsidian_writer.py)                        │
│     └─> Generate YAML frontmatter                              │
│     └─> Write .md files to vault                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Processing Breakdown by Component

| Component | Tool/Library | LLM Used? | Purpose |
|-----------|-------------|-----------|---------|
| **URL Fetching** | requests | ❌ No | Download HTML |
| **HTML Parsing** | BeautifulSoup | ❌ No | Parse DOM structure |
| **Boilerplate Removal** | BeautifulSoup + CSS selectors | ❌ No | Remove nav, footer, ads |
| **Content Extraction** | BeautifulSoup | ❌ No | Get main text content |
| **Markdown Conversion** | markdownify | ❌ No | HTML → Markdown |
| **Link Discovery** | BeautifulSoup | ❌ No | Extract <a> tags |
| **Title Improvement** | LangChain + Llama 3.1 | ✅ **YES** | Enhance title clarity |
| **Tag Extraction** | LangChain + Llama 3.1 | ✅ **YES** | Generate relevant tags |
| **Slug Generation** | python-slugify + hashlib | ❌ No | Create URL-safe filename |
| **File Writing** | Python pathlib | ❌ No | Write .md files |

## 🎯 Specific LLM Usage

### Location: `llm_normalizer.py` (lines 27-122)

**Function 1: `improve_title()`**
```python
# Input received from ContentProcessor
title = "Example Domain"  # Extracted by BeautifulSoup
content_preview = "This domain is for use in..."  # First 500 chars

# LLM Prompt (via LangChain)
prompt = """
You are a helpful assistant that improves web page titles.
Create a clear, concise title (max 80 chars).
Return ONLY a JSON object: {"title": "improved title"}
"""

# LLM processes with Llama 3.1:8b
response = llm.invoke(prompt)

# Output
improved_title = "Use as Example Domain in Documents"
```

**Function 2: `extract_tags()`**
```python
# Input received from ContentProcessor
title = "Use as Example Domain in Documents"
content_sample = content[:1000]  # First 1000 chars

# LLM Prompt (via LangChain)
prompt = """
You are a helpful assistant that extracts relevant tags.
Return ONLY a JSON object: {"tags": ["tag1", "tag2", "tag3"]}
Include 3-7 relevant, lowercase tags.
"""

# LLM processes with Llama 3.1:8b
response = llm.invoke(prompt)

# Output
tags = ["example", "domain", "illustration", "documentation", "reference"]
```

## ⏱️ Performance Impact

From our test results:

- **Without LLM** (`--skip-llm`): ~0.5 seconds per page
- **With LLM**: ~4-5 seconds per page
  - Title improvement: ~2 seconds
  - Tag extraction: ~2 seconds
  - **10x slower but adds semantic value**

## 🔄 Can You Run Without LLM?

**Yes!** Use the `--skip-llm` flag:

```bash
python main.py --skip-llm
```

When skipped:
- ✅ Crawling still works
- ✅ Content extraction still works
- ✅ Markdown conversion still works
- ✅ Obsidian files still created
- ❌ Title remains as-extracted from HTML
- ❌ Tags default to `["crawled"]`

## 🎓 Summary

**The LLM (Llama 3.1 via LangChain) is used as a POST-PROCESSOR:**

1. ❌ **NOT** for crawling decisions
2. ❌ **NOT** for HTML parsing
3. ❌ **NOT** for content extraction
4. ✅ **ONLY** for semantic enhancement:
   - Making titles more descriptive
   - Generating contextual tags

**It's an optional enhancement layer** that adds intelligence to the metadata, but the core crawler works perfectly without it using traditional web scraping techniques (BeautifulSoup, markdownify, etc.).

---

**Key Insight:** The crawler uses a **hybrid approach**:
- Traditional libraries for **reliable, fast parsing**
- LLM for **semantic understanding and enhancement**
