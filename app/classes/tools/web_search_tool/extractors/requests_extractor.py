import requests
import re
from html import unescape
from typing import Optional
from ..search_result import SearchResult
import logging

logger = logging.getLogger(__name__)

def extract(url: str, source: str = "Web") -> Optional[SearchResult]:
    """Fallback content extraction using requests and basic HTML parsing."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        content = response.text
        
        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = unescape(title_match.group(1)) if title_match else "Untitled"
        
        # Remove HTML tags and clean up
        text_content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
        text_content = re.sub(r'<[^>]+>', ' ', text_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Create snippet and limit content
        content_text = text_content[:2000] + "..." if len(text_content) > 2000 else text_content
        
        return SearchResult(
            title=title,
            url=url,
            snippet=content_text[:200] if content_text else "",
            content=content_text,
            source=source
        )
        
    except Exception as e:
        logger.error(f"Requests extraction failed for {url}: {e}")
        return None