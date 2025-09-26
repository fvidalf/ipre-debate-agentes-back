from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models import RunEvent, RunAnalytics, Run
from ..classes.nlp import SentenceEmbedder


class AnalyticsService:
    """Service for computing and caching simulation analytics"""
    
    def __init__(self, sentence_embedder: Optional[SentenceEmbedder] = None):
        self.embedder = sentence_embedder
    
    def get_or_compute_analytics(self, run_id: UUID, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get analytics for a run. If not cached, compute and cache them.
        Uses short-lived DB session pattern like the rest of the app.
        """
        # Check if analytics already exist
        existing_analytics = db.get(RunAnalytics, run_id)
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
        """Compute analytics from RunEvent data"""
        
        # Get all events for this run, ordered by iteration
        stmt = select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.iteration)
        events = db.exec(stmt).all()
        
        if not events:
            return None
        
        # Extract unique agent names from all events
        all_agents = set()
        for event in events:
            all_agents.add(event.speaker)
            all_agents.update(event.engaged)
        
        agent_names = sorted(list(all_agents))
        agent_to_index = {name: idx for idx, name in enumerate(agent_names)}
        
        # Build engagement matrix: [agent_index][turn] -> 0=inactive, 1=engaged, 2=speaking
        engagement_matrix = []
        turn_count = len(events)
        
        for agent_idx in range(len(agent_names)):
            agent_row = []
            for event in events:
                agent_name = agent_names[agent_idx]
                if agent_name == event.speaker:
                    agent_row.append(2)  # Speaking
                elif agent_name in event.engaged:
                    agent_row.append(1)  # Engaged
                else:
                    agent_row.append(0)  # Inactive
            engagement_matrix.append(agent_row)
        
        # Compute participation stats
        participation_stats = self._compute_participation_stats(events, agent_names)
        
        # Compute opinion similarity matrix using final opinions
        opinion_similarity_matrix = self._compute_opinion_similarity(events, agent_names)
        
        return {
            "engagement_matrix": engagement_matrix,
            "agent_names": agent_names,
            "participation_stats": participation_stats,
            "opinion_similarity_matrix": opinion_similarity_matrix
        }
    
    def _compute_participation_stats(self, events: List[RunEvent], agent_names: List[str]) -> Dict[str, Any]:
        """Compute participation statistics from events"""
        
        # Initialize counters
        total_interventions = {name: 0 for name in agent_names}
        total_engagements = {name: 0 for name in agent_names}
        
        # Count interventions and engagements
        for event in events:
            # Count speaking interventions
            total_interventions[event.speaker] += 1
            
            # Count engagements (times agent reacted to someone else)
            for engaged_agent in event.engaged:
                if engaged_agent in total_engagements:
                    total_engagements[engaged_agent] += 1
        
        # Calculate engagement rates (engagements / total_turns)
        total_turns = len(events)
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
    
    def _compute_opinion_similarity(self, events: List[RunEvent], agent_names: List[str]) -> Optional[List[List[float]]]:
        """Compute opinion similarity matrix using final opinions of each agent"""
        
        if not self.embedder:
            # If no embedder available, return None (similarity matrix will be omitted)
            return None
        
        # Get the last opinion from each agent
        agent_final_opinions = {}
        
        # Go through events in reverse to get the last opinion from each agent
        for event in reversed(events):
            if event.speaker not in agent_final_opinions:
                agent_final_opinions[event.speaker] = event.opinion
        
        # Ensure we have opinions for all agents (some might not have spoken)
        final_opinions = []
        valid_agent_names = []
        
        for agent_name in agent_names:
            if agent_name in agent_final_opinions:
                final_opinions.append(agent_final_opinions[agent_name])
                valid_agent_names.append(agent_name)
        
        if len(final_opinions) < 2:
            return None  # Need at least 2 opinions to compute similarity
        
        # Compute similarity matrix
        similarity_matrix = []
        
        for i, opinion_i in enumerate(final_opinions):
            similarity_row = []
            for j, opinion_j in enumerate(final_opinions):
                if i == j:
                    similarity_row.append(1.0)  # Self-similarity is 1.0
                else:
                    similarity = self.embedder.text_similarity_score(opinion_i, opinion_j)
                    similarity_row.append(float(similarity))  # Ensure it's a regular float
            similarity_matrix.append(similarity_row)
        
        return similarity_matrix
    
    def _format_analytics_response(self, analytics: RunAnalytics) -> Dict[str, Any]:
        """Format analytics data for API response"""
        response = {
            "run_id": str(analytics.run_id),
            "engagement_matrix": {
                "data": analytics.engagement_matrix,
                "agent_names": analytics.agent_names,
                "turn_count": len(analytics.engagement_matrix[0]) if analytics.engagement_matrix else 0,
                "legend": {
                    "0": "inactive",
                    "1": "engaged", 
                    "2": "speaking"
                }
            },
            "participation_stats": analytics.participation_stats,
            "computed_at": analytics.computed_at.isoformat()
        }
        
        # Include opinion similarity matrix if available
        if analytics.opinion_similarity_matrix:
            response["opinion_similarity"] = {
                "matrix": analytics.opinion_similarity_matrix,
                "agent_names": analytics.agent_names
            }
        
        return response