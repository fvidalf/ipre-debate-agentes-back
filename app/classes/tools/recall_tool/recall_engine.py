"""
Core recall engine for embedding-based information retrieval.

This module handles the core logic for querying embeddings and formatting results,
abstracted away from tool creation and document management.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import numpy as np

from sqlmodel import Session, select, and_, or_, func
from app.models import Embedding, Intervention, ToolUsage
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class RecallEngine:
    """Core engine for embedding-based recall operations."""
    
    def __init__(self, engine):
        self.engine = engine
    
    def query_embeddings(
        self,
        query: str,
        agent_name: str,
        run_id: UUID,
        source_types: List[str],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Query embeddings for relevant information.
        
        Args:
            query: Search query text
            agent_name: Name of the agent making the query
            run_id: Current simulation run ID
            source_types: Types of sources to search ('document', 'intervention', etc.)
            limit: Maximum number of results to return
            
        Returns:
            List of result dictionaries with similarity scores and metadata
        """
        try:
            # Generate query embedding
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.encode(query)
            query_vector = query_embedding[0] if query_embedding.ndim > 1 else query_embedding
            
            with Session(self.engine) as db:
                # Build query with pgvector cosine distance
                stmt = (
                    select(
                        Embedding.source_type,
                        Embedding.source_id,
                        Embedding.text_content,
                        Embedding.visibility,
                        Embedding.owner_agent,
                        Embedding.extra_metadata,
                        (1 - func.op('<=>')(Embedding.embedding, query_vector.tolist())).label('similarity')
                    )
                    .where(
                        and_(
                            Embedding.run_id == run_id,
                            Embedding.source_type.in_(source_types),
                            or_(
                                Embedding.visibility == "public",
                                and_(
                                    Embedding.visibility == "private",
                                    Embedding.owner_agent == agent_name
                                )
                            )
                        )
                    )
                    .order_by(func.op('<=>')(Embedding.embedding, query_vector.tolist()))
                    .limit(limit)
                )
                
                results = db.exec(stmt).fetchall()
                
                # Convert to list of dictionaries
                return [
                    {
                        'source_type': result.source_type,
                        'source_id': result.source_id,
                        'text_content': result.text_content,
                        'visibility': result.visibility,
                        'owner_agent': result.owner_agent,
                        'extra_metadata': result.extra_metadata,
                        'similarity': round(result.similarity, 3)
                    }
                    for result in results
                ]
                
        except Exception as e:
            logger.error(f"Error querying embeddings: {e}")
            return []
    
    def format_results(
        self,
        results: List[Dict[str, Any]],
        query: str
    ) -> str:
        """
        Format query results into human-readable text.
        
        Args:
            results: List of result dictionaries from query_embeddings
            query: Original search query
            
        Returns:
            Formatted text string for agent consumption
        """
        if not results:
            return f"No relevant information found for query: {query}"
        
        # Collect detailed information by joining with source tables
        recall_items = []
        
        with Session(self.engine) as db:
            for result in results:
                source_type = result['source_type']
                source_id = result['source_id']
                similarity = result['similarity']
                text_content = result['text_content']
                
                if source_type == "intervention":
                    intervention = db.get(Intervention, source_id)
                    if intervention:
                        recall_items.append(
                            f"[Intervention by {intervention.speaker}, similarity: {similarity}]\n{intervention.content}"
                        )
                
                elif source_type in ["tool_query", "tool_output"]:
                    tool_usage = db.get(ToolUsage, source_id)
                    if tool_usage:
                        content_type = "searched for" if source_type == "tool_query" else "found"
                        recall_items.append(
                            f"[{tool_usage.agent_name} {content_type} using {tool_usage.tool_name}, similarity: {similarity}]\n{text_content}"
                        )
                
                elif source_type == "document":
                    # For documents, use the text content directly with metadata
                    metadata = result.get('extra_metadata', {})
                    doc_title = metadata.get('document_title', 'Document')
                    recall_items.append(
                        f"[Document: {doc_title}, similarity: {similarity}]\n{text_content}"
                    )
        
        if not recall_items:
            return f"No accessible information found for query: {query}"
        
        return "\n\n".join(recall_items)