# 🚀 Quick Start Guide

## 5-Minute Setup

```bash
# 1. Navigate to project
cd ~/dev/python-llama-demo/python-ai-crawler-scraper

# 2. Activate virtual environment
source ../venv/bin/activate

# 3. Run setup
./setup.sh

# 4. Create basic .env (if needed)
echo "SEED_URLS=https://example.com" > .env

# 5. Run your first crawl!
python main.py --seeds https://example.com --max-pages 5 --skip-llm
```

## Common Commands

```bash
# Small test crawl (no LLM, fast)
python main.py --seeds https://example.com --max-pages 5 --skip-llm

# Full crawl with LLM enhancement
python main.py --seeds https://docs.python.org --max-pages 25 --max-depth 2

# Resume interrupted crawl
python main.py --resume

# Domain-restricted crawl
python main.py --seeds https://example.com --allowed-domains example.com
```

## What You Get

After crawling, find your results in:
- **Database**: `crawler.db` (SQLite with all pages and links)
- **Obsidian Vault**: `obsidian_vault/` directory with `.md` files

## Output Structure

```
obsidian_vault/
├── example-com-homepage.md
├── about-us.md
├── contact-page.md
└── ... (one .md file per page)
```

Each file contains:
- YAML frontmatter with metadata
- Clean Markdown content
- Wiki-links to other pages
- Backlinks list

## Need Help?

- **Full docs**: See `README.md`
- **Architecture**: See `SUMMARY.md`  
- **Test modules**: `python <module>.py`
- **Configuration**: Edit `.env` file

## Troubleshooting

**LLM not working?**
```bash
python main.py --skip-llm
```

**Too slow?**
```bash
# Increase delay in .env
REQUEST_DELAY=2.0
```

**Want more control?**
```bash
python main.py --help
```

---

**That's it!** You're ready to crawl. See README.md for advanced features.
