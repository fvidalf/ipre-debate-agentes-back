from typing import Any, Dict
from .searchers.pse_search import search_pse
from .searchers.google_ai_search import search_google_ai
from .config import WebSearchConfig
from .extractors import extract
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from .utils import deduplicate_urls
from .summarizer import aggregate_results

logger = logging.getLogger(__name__)


class WebSearchEngine:
    _cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self, config: WebSearchConfig):
        self.config = config
    
    def search(self, query: str) -> Dict[str, Any]:
        # logger.info(f"WebSearchEngine: Starting search for query: '{query}'")
        try:
            # Phase 1: Get URLs from PSE and Google AI
            pse_results = search_pse(query, self.config, self._cache)
            google_ai_summary, google_ai_snippets, google_ai_urls = search_google_ai(query, self.config, self._cache)
            
            all_urls = deduplicate_urls([r.url for r in pse_results] + google_ai_urls)

            # Phase 2: Extract content from URLs (parallelized)
            content_results = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_url = {executor.submit(extract, url, self.config): url for url in all_urls}
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        if result:
                            content_results.append(result)
                    except Exception as e:
                        logger.error(f"Parallel extraction failed for {url}: {e}")

            # Phase 3: Create final summary
            final_summary = aggregate_results(content_results, google_ai_summary, google_ai_snippets, query)

            return {
                "results": content_results,
                "summary": final_summary,
                "sources": [r.url for r in content_results],
            }

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return {"results": [], "summary": f"Search failed: {e}", "sources": []}