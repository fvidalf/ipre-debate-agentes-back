import logging
from uuid import UUID
from typing import Dict, Any, List, Optional

from .config import RecallToolConfig
from .recall_engine import RecallEngine

logger = logging.getLogger(__name__)


def create_recall_tool(
    config: RecallToolConfig,
    tool_id: str = "default",
    agent_name: Optional[str] = None,
    run_id: Optional[UUID] = None,
    engine=None
) -> callable:
    """
    Create a DSPy-compatible recall tool function.

    Args:
        config: Recall tool configuration
        tool_id: Unique identifier for this tool instance
        agent_name: Name of the agent using this tool
        run_id: UUID of the current simulation run
        engine: Database engine for queries

    Returns:
        Callable recall function compatible with DSPy
    """

    def recall(query: str) -> str:
        """Recall information from documents and/or notes about a given query."""
        if not agent_name or not run_id or not engine:
            return "Error: Recall tool not properly configured with agent context"

        try:
            # Determine source types based on configuration
            source_types = []
            if config.uses_documents:
                source_types.append("document")
            if config.uses_notes:
                source_types.extend(["intervention", "tool_query", "tool_output"])

            if not source_types:
                return "No recall sources configured"

            # Use recall engine for the heavy lifting
            recall_engine = RecallEngine(engine)
            results = recall_engine.query_embeddings(
                query=query,
                agent_name=agent_name,
                run_id=run_id,
                source_types=source_types,
                limit=5
            )

            return recall_engine.format_results(results, query)

        except Exception as e:
            logger.error(f"Error in recall tool for agent {agent_name}: {e}")
            return f"Error retrieving information: {str(e)}"

    recall.__name__ = f"recall_{tool_id}"
    return recall


def create_recall_tools_for_agents(
    agent_configs: Dict[str, Dict[str, Any]],
    agent_names: List[str],
    run_id: UUID,
    engine
) -> Dict[str, callable]:
    """Create recall tools for multiple agents with different configurations."""
    tools = {}

    for i, agent_name in enumerate(agent_names):
        # Get config for this agent
        config_dict = agent_configs.get(agent_name, agent_configs.get(str(i), {}))
        config = RecallToolConfig.from_dict(config_dict)

        tool = create_recall_tool(
            config=config,
            tool_id=agent_name,
            agent_name=agent_name,
            run_id=run_id,
            engine=engine,
        )
        tools[agent_name] = tool

    return tools
