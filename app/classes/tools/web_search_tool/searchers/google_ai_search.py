import logging
from typing import List, Dict
from ..utils import get_reference_url
from ..config import WebSearchConfig
try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

logger = logging.getLogger(__name__)


def search_google_ai(query: str, config: WebSearchConfig, cache: Dict) -> tuple[str, List[str], List[str]]:
    # logger.info(f"🤖 Google AI: Starting search for query: '{query}'")
    if not config.uses_google_ai or not config.serpapi_api_key:
        # logger.info("⚠️ Google AI: Search skipped - not enabled or missing API key")
        return "", [], []

    if GoogleSearch is None:
        # logger.warning("⚠️ Google AI: SerpAPI not available - install with: pip install google-search-results")
        return "", [], []

    cache_key = f"google_ai::{query.lower().strip()}"
    if cache_key in cache:
        c = cache[cache_key]
        return c["summary"], c["snippets"], c["urls"]

    try:
        logger.info("📡 Google AI: Making SerpAPI request")
        params = {"engine": "google_ai_mode", "q": query, "api_key": config.serpapi_api_key}
        search = GoogleSearch(params)
        results = search.get_dict()

        if "error" in results:
            logger.error(f"❌ Google AI: API error - {results['error']}")
            return "", [], []

        snippets = []
        urls = set()

        text_blocks = results.get("text_blocks", [])
        
        for block in text_blocks:
            # Grab summary text
            if "snippet" in block and isinstance(block["snippet"], str):
                snippet_text = block["snippet"]
                snippets.append(snippet_text)

            # Grab list items
            if block.get("type") == "list" and isinstance(block.get("list"), list):
                list_items = block.get("list", [])
                logger.info(f"📋 Google AI: Processing list with {len(list_items)} items")
                for item in list_items:
                    if "snippet" in item:
                        item_snippet = item["snippet"]
                        snippets.append(item_snippet)

            # Collect linked references
            if "reference_indexes" in block:
                for idx in block["reference_indexes"]:
                    ref_url = get_reference_url(results, idx)
                    if ref_url:
                        urls.add(ref_url)
            if block.get("type") == "list":
                for item in block.get("list", []):
                    if "reference_indexes" in item:
                        for idx in item["reference_indexes"]:
                            ref_url = get_reference_url(results, idx)
                            if ref_url:
                                urls.add(ref_url)

        # Add quick_results + references (for completeness)
        quick_results = results.get("quick_results", [])
        references = results.get("references", [])
        logger.info(f"🔗 Google AI: Processing {len(quick_results)} quick results and {len(references)} references")
        
        for qres in quick_results:
            if "link" in qres:
                urls.add(qres["link"])
        for ref in references:
            if "link" in ref:
                urls.add(ref["link"])

        # Combine the snippets into a top-level AI summary paragraph
        ai_summary = " ".join(snippets)
        
        # Log snippet details
        total_snippet_chars = sum(len(s) for s in snippets)
        logger.info(f"📊 Google AI: Snippet analysis - Total: {total_snippet_chars} chars, Average: {total_snippet_chars//len(snippets) if snippets else 0} chars/snippet")

        # Limit URLs to maximum of 3
        urls_list = list(urls)[:3]

        # Cache it
        cache[cache_key] = {
            "summary": ai_summary,
            "snippets": snippets,
            "urls": urls_list
        }

        return ai_summary, snippets, urls_list

    except Exception as e:
        logger.error(f"Google AI search failed: {e}")
        return "", [], []