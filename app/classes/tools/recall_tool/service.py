"""
Document lifecycle management for recall tools.

This service handles assigning and releasing documents to/from agents during simulations,
keeping document management separate from tool creation.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID

from sqlmodel import Session, select
from app.models import Embedding, AgentDocumentAccess
from .config import RecallToolConfig

logger = logging.getLogger(__name__)


class RecallDocumentService:
    """Service for managing document assignments during simulations."""
    
    def __init__(self, engine):
        self.engine = engine
    
    def assign_documents_to_run(
        self,
        agent_configs: Dict[str, Dict[str, Any]],
        agent_names: List[str],
        run_id: UUID
    ) -> None:
        """
        Assign documents to agents at the start of a simulation run.
        
        Args:
            agent_configs: Dictionary mapping agent names to their recall tool configurations
            agent_names: List of agent names in the simulation
            run_id: UUID of the simulation run
        """
        try:
            with Session(self.engine) as db:
                for agent_name in agent_names:
                    config_dict = agent_configs.get(agent_name, {})
                    config = RecallToolConfig.from_dict(config_dict)
                    
                    if config.document_ids:
                        logger.info(f"Assigning {len(config.document_ids)} documents to agent {agent_name}")
                        
                        for document_id in config.document_ids:
                            # Update embeddings to assign to agent
                            stmt = (
                                select(Embedding)
                                .where(Embedding.source_type == "document")
                                .where(Embedding.source_id == document_id)
                                .where(Embedding.owner_agent.is_(None))
                                .where(Embedding.run_id.is_(None))
                            )
                            embeddings = db.exec(stmt).all()
                            
                            if not embeddings:
                                logger.warning(f"No unassigned embeddings found for document {document_id}")
                                continue
                            
                            # Assign embeddings to agent
                            for embedding in embeddings:
                                embedding.owner_agent = agent_name
                                embedding.run_id = run_id
                                db.add(embedding)
                            
                            # Create access tracking record
                            access_record = AgentDocumentAccess(
                                run_id=run_id,
                                agent_name=agent_name,
                                document_id=document_id
                            )
                            db.add(access_record)
                            
                            logger.debug(f"Assigned document {document_id} to agent {agent_name} (run: {run_id})")
                
                db.commit()
                logger.info(f"Document assignment completed for run {run_id}")
                
        except Exception as e:
            logger.error(f"Error assigning documents to run {run_id}: {e}")
            raise
    
    def release_documents_from_run(self, run_id: UUID) -> None:
        """
        Release all documents assigned to agents in a specific run.
        
        Args:
            run_id: UUID of the simulation run to clean up
        """
        try:
            with Session(self.engine) as db:
                # Reset embeddings back to unassigned state
                stmt = (
                    select(Embedding)
                    .where(Embedding.source_type == "document")
                    .where(Embedding.run_id == run_id)
                )
                embeddings = db.exec(stmt).all()
                
                document_count = 0
                for embedding in embeddings:
                    embedding.owner_agent = None
                    embedding.run_id = None
                    db.add(embedding)
                    document_count += 1
                
                db.commit()
                logger.info(f"Released {document_count} document embeddings from run {run_id}")
                
        except Exception as e:
            logger.error(f"Error releasing documents from run {run_id}: {e}")
            raise
    
    def get_agent_document_stats(self, run_id: UUID) -> Dict[str, int]:
        """
        Get statistics about document access for a run.
        
        Args:
            run_id: UUID of the simulation run
            
        Returns:
            Dictionary mapping agent names to number of assigned documents
        """
        try:
            with Session(self.engine) as db:
                stmt = (
                    select(AgentDocumentAccess.agent_name, AgentDocumentAccess.document_id)
                    .where(AgentDocumentAccess.run_id == run_id)
                )
                access_records = db.exec(stmt).all()
                
                stats = {}
                for record in access_records:
                    agent_name = record.agent_name
                    if agent_name not in stats:
                        stats[agent_name] = 0
                    stats[agent_name] += 1
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting document stats for run {run_id}: {e}")
            return {}