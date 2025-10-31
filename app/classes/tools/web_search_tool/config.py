from typing import Any, Dict, List, Optional
import os

class WebSearchConfig:
    def __init__(
        self,
        uses_google_ai: bool = False,
        uses_wikipedia: bool = False,
        uses_news: bool = False,
        uses_pages: bool = False,
        news_sources: Optional[List[str]] = None,
        page_sources: Optional[List[str]] = None,
        google_cse_id: Optional[str] = None,
        serpapi_api_key: Optional[str] = None,
    ):
        self.uses_google_ai = uses_google_ai
        self.uses_wikipedia = uses_wikipedia
        self.uses_news = uses_news
        self.uses_pages = uses_pages
        self.news_sources = news_sources or []
        self.page_sources = page_sources or []
        self.google_cse_id = google_cse_id
        self.serpapi_api_key = serpapi_api_key or os.getenv('SERPAPI_API_KEY')
        self.pse_sites = self._build_pse_sites()
    
    def _build_pse_sites(self) -> List[str]:
        sites = []
        if self.uses_wikipedia:
            sites.extend(["wikipedia.org", "en.wikipedia.org"])
        if self.uses_news and self.news_sources:
            sites.extend(self.news_sources)
        if self.uses_pages and self.page_sources:
            sites.extend(self.page_sources)
        return sites
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'WebSearchConfig':
        return cls(
            uses_google_ai=config.get('google_ai_tool', {}).get('enabled', False),
            uses_wikipedia=config.get('wikipedia_tool', {}).get('enabled', False),
            uses_news=config.get('news_tool', {}).get('enabled', False),
            uses_pages=config.get('pages_tool', {}).get('enabled', False),
            news_sources=config.get('news_tool', {}).get('sources', []),
            page_sources=config.get('pages_tool', {}).get('sources', []),
            google_cse_id=config.get('google_cse_id') or os.getenv('GOOGLE_CSE_ID'),
            serpapi_api_key=config.get('serpapi_api_key') or os.getenv('SERPAPI_API_KEY'),
        )