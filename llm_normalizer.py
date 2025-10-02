#!/usr/bin/env python3
"""
LLM-based text normalizer using LangChain with Ollama for
title improvement and content cleanup.
"""

import json
from typing import Dict, Optional
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from config import CrawlerConfig


class LLMNormalizer:
    """Uses local LLM to normalize and improve text content."""
    
    def __init__(self, config: CrawlerConfig):
        """Initialize LLM normalizer with Ollama model."""
        self.config = config
        self.llm = ChatOllama(
            model=config.LLM_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            temperature=config.LLM_TEMPERATURE,
            timeout=config.LLM_TIMEOUT
        )
    
    def improve_title(self, title: str, content_preview: str) -> str:
        """
        Improve and normalize page title using LLM.
        
        Args:
            title: Original extracted title
            content_preview: First 500 chars of content
        
        Returns:
            Improved title or original if LLM fails
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that improves web page titles. "
                      "Create a clear, concise title (max 80 chars) based on the original title and content. "
                      "Return ONLY a JSON object with format: {{\"title\": \"improved title\"}}"),
            ("human", f"Original title: {title}\n\nContent preview: {content_preview[:500]}")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({})
            
            # Parse JSON response
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response
            json_match = response_text.strip()
            if not json_match.startswith('{'):
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{[^}]+\}', response_text)
                if json_match:
                    json_match = json_match.group()
                else:
                    return title
            
            data = json.loads(json_match)
            improved_title = data.get('title', title)
            
            # Validate improved title
            if improved_title and len(improved_title) > 3 and len(improved_title) <= 80:
                return improved_title
            
            return title
        
        except Exception as e:
            print(f"⚠️  LLM title improvement failed: {e}")
            return title
    
    def extract_tags(self, title: str, content: str) -> list:
        """
        Extract relevant tags from content using LLM.
        
        Args:
            title: Page title
            content: Page content (truncated)
        
        Returns:
            List of tags
        """
        # Truncate content for efficiency
        content_sample = content[:1000]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that extracts relevant tags from web page content. "
                      "Return ONLY a JSON object with format: {{\"tags\": [\"tag1\", \"tag2\", \"tag3\"]}}. "
                      "Include 3-7 relevant, lowercase tags."),
            ("human", f"Title: {title}\n\nContent: {content_sample}")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({})
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON
            import re
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
                tags = data.get('tags', [])
                
                # Validate and clean tags
                cleaned_tags = []
                for tag in tags[:7]:  # Max 7 tags
                    if isinstance(tag, str) and 2 <= len(tag) <= 20:
                        cleaned_tags.append(tag.lower().strip())
                
                return cleaned_tags if cleaned_tags else [self.config.TAG_PREFIX]
            
            return [self.config.TAG_PREFIX]
        
        except Exception as e:
            print(f"⚠️  LLM tag extraction failed: {e}")
            return [self.config.TAG_PREFIX]


if __name__ == "__main__":
    # Test LLM normalizer
    normalizer = LLMNormalizer(CrawlerConfig)
    
    # Test title improvement
    test_title = "Untitled - Page 1"
    test_content = "This is a comprehensive guide to Python web scraping with BeautifulSoup and requests."
    
    print("Testing LLM Normalizer...")
    print(f"Original title: {test_title}")
    
    try:
        improved = normalizer.improve_title(test_title, test_content)
        print(f"Improved title: {improved}")
        
        tags = normalizer.extract_tags(improved, test_content)
        print(f"Extracted tags: {tags}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
