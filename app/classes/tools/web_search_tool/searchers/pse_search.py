import logging
from ..search_result import SearchResult
from ..config import WebSearchConfig
from typing import Dict, List
from google.oauth2 import service_account
import os
import requests
import google.auth.transport.requests


logger = logging.getLogger(__name__)


def search_pse(query: str, config: WebSearchConfig, cache: Dict) -> List[SearchResult]:
    # logger.info(f"🔍 PSE: Starting search for query: '{query}'")
    cache_key = f"pse::{query.lower().strip()}"
    if cache_key in cache:
        return cache[cache_key]["results"]

    if not config.google_cse_id:
        logger.warning("⚠️ PSE: Search skipped - missing CSE ID")
        return []
    
    try:
        # Load service account credentials
        creds = service_account.Credentials.from_service_account_file(
            os.getenv('GOOGLE_CREDENTIALS_PATH'), 
            scopes=["https://www.googleapis.com/auth/cse"]
        )
        
        # Refresh and get a valid access token
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        token = creds.token

        # Build your query parameters
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "cx": config.google_cse_id,
            "q": query,
            "num": 3
        }

        if config.pse_sites:
            site_restriction = " OR ".join([f"site:{site}" for site in config.pse_sites])
            params["q"] = f'({query}) ({site_restriction})'
            # logger.info(f"🌐 PSE: Applied site restrictions: {config.pse_sites}")

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])
        # logger.info(f"📊 PSE: Received {len(items)} search results")

        results = []
        for item in items:
            result = SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="PSE"
            )
            results.append(result)

        cache[cache_key] = {"results": results}
        return results

    except Exception as e:
        logger.error(f"PSE search failed: {e}")
        return []