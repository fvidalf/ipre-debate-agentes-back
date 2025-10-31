from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlmodel import SQLModel

from ..models import Intervention, RunAnalytics, Run


class AnalyticsService:
    """Service for computing and caching simulation analytics"""
    
    def get_or_compute_analytics(self, run_id: UUID, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get analytics for a run. If not cached, compute and cache them.
        Uses short-lived DB session pattern like the rest of the app.
        """
        # Check if analytics already exist - query by run_id, not primary key
        existing_analytics = db.query(RunAnalytics).filter(RunAnalytics.run_id == run_id).first()
        if existing_analytics:
            return self._format_analytics_response(existing_analytics)
        
        # Verify run exists and is finished
        run = db.get(Run, run_id)
        if not run:
            return None
        
        if not run.finished:
            return {"error": "Simulation must be finished to generate analytics"}
        
        # Compute analytics
        analytics_data = self._compute_analytics(run_id, db)
        if not analytics_data:
            return None
        
        # Cache in database
        analytics = RunAnalytics(
            run_id=run_id,
            engagement_matrix=analytics_data["engagement_matrix"],
            agent_names=analytics_data["agent_names"],
            participation_stats=analytics_data["participation_stats"],
            opinion_similarity_matrix=analytics_data["opinion_similarity_matrix"]
        )
        
        db.add(analytics)
        db.commit()
        db.refresh(analytics)
        
        return self._format_analytics_response(analytics)
    
    def _compute_analytics(self, run_id: UUID, db: Session) -> Optional[Dict[str, Any]]:
        """Compute analytics from Intervention data"""
        
        # Get all interventions for this run, ordered by iteration
        # Use SQLAlchemy query method for better compatibility
        interventions = db.query(Intervention).filter(Intervention.run_id == run_id).order_by(Intervention.iteration).all()
        
        if not interventions:
            return None
        
        # Extract unique agent names from all interventions
        all_agents = set()
        for intervention in interventions:
            all_agents.add(intervention.speaker)
            all_agents.update(intervention.engaged_agents)
        
        agent_names = sorted(list(all_agents))
        agent_to_index = {name: idx for idx, name in enumerate(agent_names)}
        
        # Build engagement matrix: [agent_index][turn] -> 0=inactive, 1=engaged, 2=speaking
        engagement_matrix = []
        turn_count = len(interventions)
        
        for agent_idx in range(len(agent_names)):
            agent_row = []
            for intervention in interventions:
                agent_name = agent_names[agent_idx]
                if agent_name == intervention.speaker:
                    agent_row.append(2)  # Speaking
                elif agent_name in intervention.engaged_agents:
                    agent_row.append(1)  # Engaged
                else:
                    agent_row.append(0)  # Inactive
            engagement_matrix.append(agent_row)
        
        # Compute participation stats
        participation_stats = self._compute_participation_stats(interventions, agent_names)
        
        # Compute opinion similarity matrix using final opinions
        opinion_similarity_matrix = self._compute_opinion_similarity(interventions, agent_names)
        
        return {
            "engagement_matrix": engagement_matrix,
            "agent_names": agent_names,
            "participation_stats": participation_stats,
            "opinion_similarity_matrix": opinion_similarity_matrix
        }
    
    def _compute_participation_stats(self, interventions: List[Intervention], agent_names: List[str]) -> Dict[str, Any]:
        """Compute participation statistics from events"""
        
        # Initialize counters
        total_interventions = {name: 0 for name in agent_names}
        total_engagements = {name: 0 for name in agent_names}
        
        # Count interventions and engagements
        for intervention in interventions:
            # Count speaking interventions
            total_interventions[intervention.speaker] += 1
            
            # Count engagements (times agent reacted to someone else)
            for engaged_agent in intervention.engaged_agents:
                if engaged_agent in total_engagements:
                    total_engagements[engaged_agent] += 1
        
        # Calculate engagement rates (engagements / total_turns)
        total_turns = len(interventions)
        engagement_rates = {
            name: total_engagements[name] / total_turns if total_turns > 0 else 0
            for name in agent_names
        }
        
        # Calculate participation percentages
        total_all_interventions = sum(total_interventions.values())
        participation_percentages = {
            name: (total_interventions[name] / total_all_interventions * 100) if total_all_interventions > 0 else 0
            for name in agent_names
        }
        
        return {
            "total_interventions": total_interventions,
            "total_engagements": total_engagements,
            "engagement_rates": engagement_rates,
            "participation_percentages": participation_percentages,
            "total_turns": total_turns
        }
    
    def _compute_opinion_similarity(self, interventions: List[Intervention], agent_names: List[str]) -> Optional[Dict[str, Any]]:
        """Compute opinion similarity matrix using final opinions of each agent"""
        
        try:
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
        except Exception:
            # If embedding service fails, return None (similarity matrix will be omitted)
            return None
        
        # Get the last opinion from each agent
        agent_final_opinions = {}
        
        # Go through interventions in reverse to get the last opinion from each agent
        for intervention in reversed(interventions):
            if intervention.speaker not in agent_final_opinions:
                agent_final_opinions[intervention.speaker] = intervention.content
        
        # Only include agents who actually spoke
        speaking_agents = []
        final_opinions = []
        
        for agent_name in agent_names:
            if agent_name in agent_final_opinions:
                speaking_agents.append(agent_name)
                final_opinions.append(agent_final_opinions[agent_name])
        
        if len(final_opinions) < 2:
            return None  # Need at least 2 opinions to compute similarity
        
        # Compute similarity matrix with explicit agent mappings
        similarity_data = {}
        
        for i, agent_i in enumerate(speaking_agents):
            for j, agent_j in enumerate(speaking_agents):
                if i == j:
                    similarity_data[f"{agent_i}_vs_{agent_j}"] = 1.0  # Self-similarity is 1.0
                else:
                    similarity = embedding_service.text_similarity_score(final_opinions[i], final_opinions[j])
                    similarity_data[f"{agent_i}_vs_{agent_j}"] = float(similarity)
        
        # Also create traditional matrix format for backwards compatibility
        similarity_matrix = []
        for i, opinion_i in enumerate(final_opinions):
            similarity_row = []
            for j, opinion_j in enumerate(final_opinions):
                if i == j:
                    similarity_row.append(1.0)  # Self-similarity is 1.0
                else:
                    similarity = embedding_service.text_similarity_score(opinion_i, opinion_j)
                    similarity_row.append(float(similarity))  # Ensure it's a regular float
            similarity_matrix.append(similarity_row)
        
        return {
            "matrix": similarity_matrix,
            "speaking_agents": speaking_agents,
            "similarity_pairs": similarity_data
        }
    
    def _format_analytics_response(self, analytics: RunAnalytics) -> Dict[str, Any]:
        """Format analytics data for API response with structured analytics array"""
        
        # Build analytics array with individual analytic objects
        analytics_array = []
        
        # Engagement Matrix Analytics
        analytics_array.append({
            "type": "engagement_matrix",
            "title": "Agent Engagement Matrix",
            "description": "Shows agent activity patterns across debate turns",
            "data": analytics.engagement_matrix,
            "metadata": {
                "agent_names": analytics.agent_names,
                "turn_count": len(analytics.engagement_matrix[0]) if analytics.engagement_matrix else 0,
                "legend": {
                    "0": "inactive",
                    "1": "engaged", 
                    "2": "speaking"
                }
            }
        })
        
        # Participation Statistics Analytics
        analytics_array.append({
            "type": "participation_stats",
            "title": "Participation Statistics",
            "description": "Agent intervention counts, engagement rates, and participation percentages",
            "data": analytics.participation_stats,
            "metadata": {
                "agent_names": analytics.agent_names
            }
        })
        
        # Opinion Similarity Analytics (if available)
        if analytics.opinion_similarity_matrix:
            # Extract the speaking agents and similarity data from the stored structure
            similarity_data = analytics.opinion_similarity_matrix
            
            if isinstance(similarity_data, dict) and "speaking_agents" in similarity_data:
                # New format with explicit agent mappings
                analytics_array.append({
                    "type": "opinion_similarity",
                    "title": "Opinion Similarity Matrix",
                    "description": "Semantic similarity between agents' final opinions",
                    "data": {
                        "matrix": similarity_data["matrix"],
                        "similarity_pairs": similarity_data["similarity_pairs"]
                    },
                    "metadata": {
                        "speaking_agents": similarity_data["speaking_agents"],
                        "similarity_range": {"min": 0.0, "max": 1.0},
                        "note": "Higher values indicate more similar opinions. Only agents who spoke are included."
                    }
                })
            else:
                # Fallback for old format (backwards compatibility)
                analytics_array.append({
                    "type": "opinion_similarity",
                    "title": "Opinion Similarity Matrix",
                    "description": "Semantic similarity between agents' final opinions",
                    "data": similarity_data,
                    "metadata": {
                        "agent_names": analytics.agent_names,
                        "similarity_range": {"min": 0.0, "max": 1.0},
                        "note": "Higher values indicate more similar opinions"
                    }
                })
        
        response = {
            "run_id": str(analytics.run_id),
            "computed_at": analytics.computed_at.isoformat(),
            "analytics": analytics_array
        }
        
        return response