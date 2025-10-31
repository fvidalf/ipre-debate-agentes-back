from ..search_result import SearchResult
import requests
from urllib.parse import urlparse, quote, unquote
import logging
from typing import Optional
import re
from ..config import WebSearchConfig

logger = logging.getLogger(__name__)


def extract(url: str, config: WebSearchConfig) -> Optional[SearchResult]:
    # logger.info(f"📚 Wikipedia: Extracting content from URL: {url}")

    if not config.uses_wikipedia:
        return None

    try:
        # --- Parse language and page title ---
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        lang = host.split(".")[0] if host.endswith("wikipedia.org") else "en"

        match = re.search(r"/wiki/([^#?]+)", parsed.path)
        if not match:
            logger.warning("⚠️ Wikipedia: Could not extract page title from URL")
            return None

        raw_title = unquote(match.group(1))
        encoded_title = quote(raw_title, safe="")  # Percent-encode (safely)
        title_for_query = raw_title.replace("_", " ")

        # --- Proper headers (Wikimedia blocks generic clients) ---
        headers = {
            "User-Agent": "AgentsWikipediaSearch/1.0 (contact: fvidalf@uc.cl)",
            "Accept": "application/json",
        }

        # --- REST summary endpoint (fast) ---
        summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        response = requests.get(summary_url, headers=headers, timeout=10)
        response.raise_for_status()
        summary_data = response.json()

        # --- Fallback to Action API for full text (if needed) ---
        content_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": title_for_query,
            "prop": "extracts",
            "explaintext": True,
            "redirects": 1,
        }
        content_response = requests.get(content_url, headers=headers, params=params, timeout=10)
        content_response.raise_for_status()
        content_data = content_response.json()

        # Extract main text
        pages = content_data.get("query", {}).get("pages", {})
        full_content = ""
        for _, page in pages.items():
            if "extract" in page:
                full_content = page["extract"]
                break

        # --- Build result ---
        title = summary_data.get("title", title_for_query)
        description = summary_data.get("description", "")
        snippet = description if len(description) < 300 else description[:300] + "..."
        extract = summary_data.get("extract", "")

        # Prefer Action API full text if it's richer
        content = full_content or extract
        original_length = len(content)
        if len(content) > 2000:
            content = content[:2000] + "..."

        return SearchResult(
            title=title,
            url=url,
            snippet=snippet,
            content=content,
            source="Wikipedia"
        )

    except Exception as e:
        logger.error(f"Wikipedia extraction failed: {e}")
        return None