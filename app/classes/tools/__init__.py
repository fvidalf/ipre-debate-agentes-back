"""
Unified tools interface for agent capabilities.

This module provides a clean interface to all available tools,
allowing easy import and instantiation of different tool types.
"""

# Import factory functions from each tool
from .web_search_tool.factory import (
    create_web_search_tool,
    create_web_search_tools_for_agents
)
from .recall_tool.factory import (
    create_recall_tool,
    create_recall_tools_for_agents
)
from .recall_tool.service import RecallDocumentService

# Import configs for convenience
from .web_search_tool.config import WebSearchConfig
from .recall_tool.config import RecallToolConfig

# Re-export everything
__all__ = [
    # Web Search Tools
    "create_web_search_tool",
    "create_web_search_tools_for_agents",
    "WebSearchConfig",
    
    # Recall Tools  
    "create_recall_tool",
    "create_recall_tools_for_agents",
    "RecallDocumentService",
    "RecallToolConfig",
]