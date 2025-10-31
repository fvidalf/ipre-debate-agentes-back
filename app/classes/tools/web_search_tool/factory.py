
import logging
from typing import Dict, Any
from .config import WebSearchConfig
from .engine import WebSearchEngine

logger = logging.getLogger(__name__)

# Global registry for WebSearchEngine instances
_search_engines: Dict[str, WebSearchEngine] = {}


def create_web_search_tool(config: WebSearchConfig, tool_id: str = "default") -> callable:
    """Create a DSPy-compatible web search tool function."""
    _search_engines[tool_id] = WebSearchEngine(config)
    
    def web_search(query: str) -> str:
        """Search the web for information about a given query."""
        # logger.info(f"🔍 WebSearch Tool [{tool_id}]: Received query: '{query}'")
        try:
            engine = _search_engines.get(tool_id)
            if not engine:
                error_msg = f"Error: WebSearch tool {tool_id} not properly initialized"
                logger.error(f"❌ WebSearch Tool [{tool_id}]: {error_msg}")
                return error_msg

            results = engine.search(query)
            summary = results["summary"] if results["summary"] else f"No results found for query: {query}"
            # logger.info(f"✅ WebSearch Tool [{tool_id}]: Completed search - returning {len(summary)} char summary")
            return summary
                
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            logger.error(f"❌ WebSearch Tool [{tool_id}]: {error_msg}")
            return error_msg
    
    web_search.__name__ = f"web_search_{tool_id}"
    return web_search


def create_web_search_tools_for_agents(agent_configs: Dict[str, Dict[str, Any]]) -> Dict[str, callable]:
    """Create web search tools for multiple agents with different configurations."""
    tools = {}

    for agent_id, config_dict in agent_configs.items():
        config = WebSearchConfig.from_dict(config_dict)
        tool = create_web_search_tool(config, tool_id=agent_id)
        tools[agent_id] = tool

    return tools
    
