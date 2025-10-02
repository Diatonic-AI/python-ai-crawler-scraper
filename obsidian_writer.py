#!/usr/bin/env python3
"""Obsidian-compatible Markdown file writer with YAML frontmatter."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List


class ObsidianWriter:
    """Writes pages as Obsidian-compatible Markdown files."""
    
    def __init__(self, vault_dir: Path):
        """Initialize writer with vault directory."""
        self.vault_dir = vault_dir
        self.vault_dir.mkdir(parents=True, exist_ok=True)
    
    def write_page(self, page_data: Dict, backlinks: List[Dict]) -> Path:
        """
        Write page to vault as Markdown file with frontmatter.
        
        Args:
            page_data: Page data from database
            backlinks: List of backlink dictionaries
        
        Returns:
            Path to written file
        """
        # Generate filename from slug
        filename = f"{page_data['slug']}.md"
        filepath = self.vault_dir / filename
        
        # Build frontmatter
        frontmatter = self._build_frontmatter(page_data, backlinks)
        
        # Get markdown content
        markdown = page_data.get('markdown_content', '')
        
        # Write file
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
        
        # Tags
        metadata = page_data.get('metadata', {})
        tags = metadata.get('tags', ['web', 'crawled'])
        lines.append(f"tags: [{', '.join(tags)}]")
        
        # Backlinks
        if backlinks:
            lines.append("backlinks:")
            for bl in backlinks[:10]:  # Limit to 10
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
