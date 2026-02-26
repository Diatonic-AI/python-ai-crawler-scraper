#!/usr/bin/env python3
"""Obsidian-compatible Markdown file writer with YAML frontmatter."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse


class ObsidianWriter:
    """Writes pages as Obsidian-compatible Markdown files."""
    
    def __init__(self, vault_dir: Path):
        """Initialize writer with vault directory."""
        self.vault_dir = vault_dir
        self.vault_dir.mkdir(parents=True, exist_ok=True)
    
    def write_page(self, page_data: Dict, backlinks: List[Dict]) -> Path:
        """
        Write page to vault as Markdown file with frontmatter.
        """
        # Place under domain subfolder for organization
        url = page_data.get('url') or page_data.get('source_url', '')
        domain = urlparse(url).netloc if url else "unknown"
        domain_dir = self.vault_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{page_data['slug']}.md"
        filepath = domain_dir / filename
        
        frontmatter = self._build_frontmatter(page_data, backlinks)
        markdown = page_data.get('markdown_content', '')

        # Append "See also" and "Backlinks" sections if available
        see_also = page_data.get('semantic_similar') or []
        if see_also:
            markdown += "\n\n## See also\n"
            for s in see_also:
                sid = s.get('id')
                if sid:
                    markdown += f"- [[{sid}]] ({s.get('score', 0):.2f})\n"
        if backlinks:
            markdown += "\n\n## Backlinks\n"
            for bl in backlinks[:20]:
                title = bl.get('title') or bl.get('source_url') or ''
                markdown += f"- [[{title}]]\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("---\n")
            f.write(frontmatter)
            f.write("---\n\n")
            f.write(markdown)
        
        return filepath
    
    def _build_frontmatter(self, page_data: Dict, backlinks: List[Dict]) -> str:
        """Build YAML frontmatter."""
        lines = []
        
        lines.append(f"title: \"{page_data.get('title', 'Untitled')}\"")
        lines.append(f"source_url: \"{page_data.get('url', '')}\"")
        lines.append(f"slug: \"{page_data.get('slug', '')}\"")
        lines.append(f"crawled_at: \"{page_data.get('created_at', '')}\"")
        lines.append(f"updated_at: \"{page_data.get('updated_at', '')}\"")
        lines.append(f"crawl_depth: {page_data.get('crawl_depth', 0)}")
        lines.append(f"word_count: {page_data.get('word_count', 0)}")
        lines.append(f"checksum: \"{page_data.get('checksum', '')}\"")

        # Optional enrichments
        if page_data.get('summary'):
            lines.append(f"summary: \"{page_data.get('summary').replace('\\', '\\\\').replace('"', '\\"')}\"")
        if page_data.get('type'):
            lines.append(f"page_type: \"{page_data.get('type')}\"")
        if page_data.get('lang'):
            lines.append(f"lang: \"{page_data.get('lang')}\"")
        if page_data.get('embeddings_id'):
            lines.append(f"embeddings_id: \"{page_data.get('embeddings_id')}\"")

        # Tags
        metadata = page_data.get('metadata', {})
        tags = metadata.get('tags', ['web', 'crawled'])
        tags_yaml = ", ".join(tags)
        lines.append(f"tags: [{tags_yaml}]")

        # Validation results (non-blocking)
        ext_errors = page_data.get('external_link_errors') or []
        if ext_errors:
            lines.append("external_link_errors:")
            for e in ext_errors:
                lines.append(f"  - \"{e}\"")
        missing = page_data.get('missing_internal_links') or []
        if missing:
            lines.append("missing_internal_links:")
            for m in missing:
                lines.append(f"  - \"{m}\"")
        similar = page_data.get('semantic_similar') or []
        if similar:
            lines.append("semantic_similar:")
            for s in similar:
                lines.append(f"  - id: \"{s.get('id','')}\"\n    score: {s.get('score', 0)}")
        if page_data.get('last_validated'):
            lines.append(f"last_validated: \"{page_data.get('last_validated')}\"")

        # Backlinks (titles only for now)
        if backlinks:
            lines.append("backlinks:")
            for bl in backlinks[:20]:
                lines.append(f"  - \"{bl.get('title', bl.get('source_url', ''))}\"")
        
        return "\n".join(lines) + "\n"


if __name__ == "__main__":
    # Test writer
    test_dir = Path("test_vault")
    writer = ObsidianWriter(test_dir)
    
    test_data = {
        'title': 'Test Page',
        'slug': 'test-page',
        'url': 'https://example.com/test',
        'markdown_content': '# Test\n\nThis is test content.',
        'created_at': datetime.utcnow().isoformat(),
        'word_count': 5,
        'checksum': 'abc123',
        'crawl_depth': 1
    }
    
    filepath = writer.write_page(test_data, [])
    print(f"✅ Written to: {filepath}")
    
    # Cleanup
    filepath.unlink()
    test_dir.rmdir()
