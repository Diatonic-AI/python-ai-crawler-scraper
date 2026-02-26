#!/usr/bin/env python3
"""
Configuration management for the AI-powered web crawler.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


class CrawlerConfig:
    """Central configuration for the web crawler."""

    # --------------- Crawl settings ---------------
    SEED_URLS: List[str] = os.getenv("SEED_URLS", "").split(",") if os.getenv("SEED_URLS") else []
    ALLOWED_DOMAINS: List[str] = os.getenv("ALLOWED_DOMAINS", "").split(",") if os.getenv("ALLOWED_DOMAINS") else []
    MAX_DEPTH: int = int(os.getenv("MAX_DEPTH", "2"))
    MAX_PAGES: int = int(os.getenv("MAX_PAGES", "150"))
    RUNTIME_BUDGET_SEC: int = int(os.getenv("RUNTIME_BUDGET_SEC", "3600"))

    # --------------- Rate limiting ---------------
    REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "1.0"))  # seconds between requests
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # --------------- Robots policy ---------------
    ROBOTS_OBEY: bool = os.getenv("ROBOTS_OBEY", "true").lower() == "true"
    ROBOTS_FALLBACK_DELAY: float = float(os.getenv("ROBOTS_FALLBACK_DELAY", "1.0"))

    # --------------- Content filtering ---------------
    MAX_CONTENT_SIZE: int = int(os.getenv("MAX_CONTENT_SIZE", "10485760"))  # 10MB
    SKIP_EXTENSIONS: List[str] = [
        ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico",
        ".zip", ".tar", ".gz", ".bz2", ".exe", ".dmg", ".mp4",
        ".mp3", ".avi", ".mov", ".wav",
    ]
    SKIP_PATH_PATTERNS: List[str] = [
        "/api/", "/ajax/", "/json/", "/xml/",
        "/login", "/signin", "/signup", "/register",
        "/logout", "/auth/", "/oauth/",
        "/admin/", "/wp-admin/",
        "/feed/", "/rss/", "/atom/",
        "/search", "/tag/", "/category",
    ]
    STRIP_TRACKING_PARAMS: bool = os.getenv("STRIP_TRACKING_PARAMS", "true").lower() == "true"  # utm_*
    # Optional docs path restriction (e.g., "/api-reference")
    DOCS_PATH_PREFIX: str = os.getenv("DOCS_PATH_PREFIX", "")

    # --------------- Storage paths ---------------
    BASE_DIR: Path = Path(__file__).parent
    DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "crawler.db")))
    VAULT_DIR: Path = Path(os.getenv("VAULT_DIR", "/home/daclab-ai/Documents/diatonic-visuals-content/Crawls"))

    # --------------- LLM (LM Studio) ---------------
    LMSTUDIO_BASE_URL: str = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    LMSTUDIO_MODEL: str = os.getenv("LMSTUDIO_MODEL", "Llama-3.1-8B-Instruct")
    LLM_MODEL: str = os.getenv("LLM_MODEL", LMSTUDIO_MODEL)  # backward compatibility
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

    # (Deprecated Ollama fields retained for compatibility)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "")

    # --------------- Embeddings / Chroma ---------------
    EMBEDDINGS_MODEL: str = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    CHROMA_PERSIST_DIR: Path = Path(os.getenv(
        "CHROMA_PERSIST_DIR",
        str(BASE_DIR / "chroma_store"),
    ))
    CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "pages")
    SEMANTIC_TOP_K: int = int(os.getenv("SEMANTIC_TOP_K", "5"))
    SEMANTIC_THRESHOLD: float = float(os.getenv("SEMANTIC_THRESHOLD", "0.75"))

    # --------------- Validation / Linting ---------------
    VALIDATE_MARKDOWN: bool = os.getenv("VALIDATE_MARKDOWN", "true").lower() == "true"
    LINT_MARKDOWN: bool = os.getenv("LINT_MARKDOWN", "true").lower() == "true"
    EXTERNAL_LINK_RETRIES: int = int(os.getenv("EXTERNAL_LINK_RETRIES", "2"))
    EXTERNAL_LINK_TIMEOUT: int = int(os.getenv("EXTERNAL_LINK_TIMEOUT", "10"))

    # --------------- Obsidian ---------------
    USE_WIKI_LINKS: bool = os.getenv("USE_WIKI_LINKS", "true").lower() == "true"
    TAG_PREFIX: str = os.getenv("TAG_PREFIX", "crawled")

    # --------------- User agent ---------------
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (compatible; AI-Crawler/1.0; +https://example.com/bot)",
    )

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration and create necessary directories."""
        errors = []

        if not cls.SEED_URLS:
            errors.append("SEED_URLS must be provided")

        if cls.MAX_DEPTH < 1:
            errors.append("MAX_DEPTH must be at least 1")

        if cls.MAX_PAGES < 1:
            errors.append("MAX_PAGES must be at least 1")

        if cls.REQUEST_DELAY < 0:
            errors.append("REQUEST_DELAY must be non-negative")

        # Create necessary directories
        try:
            cls.VAULT_DIR.mkdir(parents=True, exist_ok=True)
            cls.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            cls.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Failed to create directories: {e}")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    @classmethod
    def display(cls):
        """Display current configuration."""
        print("\n🔧 Crawler Configuration")
        print("=" * 60)
        print(f"Seed URLs: {cls.SEED_URLS}")
        print(f"Allowed Domains: {cls.ALLOWED_DOMAINS if cls.ALLOWED_DOMAINS else 'Any'}")
        print(f"Max Depth: {cls.MAX_DEPTH}")
        print(f"Max Pages: {cls.MAX_PAGES}")
        print(f"Request Delay: {cls.REQUEST_DELAY}s (robots obey: {cls.ROBOTS_OBEY})")
        print(f"Database: {cls.DATABASE_PATH}")
        print(f"Vault Directory: {cls.VAULT_DIR}")
        print(f"LM Studio Model: {cls.LMSTUDIO_MODEL} @ {cls.LMSTUDIO_BASE_URL}")
        print(f"Embeddings: {cls.EMBEDDINGS_MODEL} → Chroma {cls.CHROMA_PERSIST_DIR} [{cls.CHROMA_COLLECTION}]")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    # Test configuration loading
    if CrawlerConfig.validate():
        CrawlerConfig.display()
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration is invalid")
