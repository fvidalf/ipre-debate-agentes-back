from urllib.parse import urlparse
from ..search_result import SearchResult
from ..config import WebSearchConfig
from . import wikipedia_extractor, newspaper_extractor, requests_extractor
import logging

logger = logging.getLogger(__name__)

def extract(url: str, config: WebSearchConfig) -> SearchResult | None:
    """Unified content extraction entry point.

    Chooses the appropriate extractor based on domain and config,
    and falls back gracefully if others fail.
    """
    domain = urlparse(url).netloc.lower()

    # 1. Wikipedia first
    if "wikipedia.org" in domain and config.uses_wikipedia:
        result = wikipedia_extractor.extract(url, config)
        if result:
            return result

    # 2️. News or general pages via Newspaper3k
    if config.uses_news and any(src in domain for src in config.news_sources):
        result = newspaper_extractor.extract(url, config, source="News")
        if result:
            return result

    # 2.5. General pages via Newspaper3k
    if config.uses_pages:
        result = newspaper_extractor.extract(url, config, source="Web")
        if result:
            return result

    # 3. Fallback to requests-based extraction
    result = requests_extractor.extract(url, source="Web")
    if result:
        return result

    logger.warning(f"No extractor succeeded for {url}")
    return None