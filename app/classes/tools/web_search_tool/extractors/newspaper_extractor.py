from newspaper import Article
from typing import Optional
from ..search_result import SearchResult
from ..config import WebSearchConfig
import logging

logger = logging.getLogger(__name__)

def extract(url: str, config: WebSearchConfig, source: str = "Web") -> Optional[SearchResult]:
    """Extract content using newspaper3k library."""

    if not (config.uses_news or config.uses_pages):
        return None

    try:
        article = Article(url)
        article.download()
        article.parse()
        title = article.title or "Untitled"
        content = article.text or ""
        
        if len(content) > 2000:
            content = content[:2000] + "..."

        return SearchResult(
            title=title,
            url=url,
            snippet=content[:200] if content else "",
            content=content,
            source=source
        )

    except Exception as e:
        logger.error(f"Newspaper extraction failed for {url}: {e}")
        return None
