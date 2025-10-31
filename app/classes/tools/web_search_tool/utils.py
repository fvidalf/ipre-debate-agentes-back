from typing import Dict, Any, List, Optional

def get_reference_url(results: Dict[str, Any], ref_index: int) -> Optional[str]:
        """Extract URL from reference by index."""
        references = results.get("references", [])
        for ref in references:
            if ref.get("index") == ref_index and "link" in ref:
                return ref["link"]
        return None
    
def deduplicate_urls(urls: List[str]) -> List[str]:
    seen = set()
    deduplicated = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduplicated.append(url)
    return deduplicated

def is_news_domain(domain: str, config) -> bool:
    return any(news_domain in domain for news_domain in config.news_sources)
