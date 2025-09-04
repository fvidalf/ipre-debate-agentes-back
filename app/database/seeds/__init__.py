"""
Seeds package - Database seeding utilities.

This package contains individual seed modules and a main runner
that can execute all seeds or specific ones.
"""

from .agents import seed_agent_templates
from .users import seed_mock_users

__all__ = ["seed_agent_templates", "seed_mock_users", "run_all_seeds"]


def run_all_seeds(session):
    """Run all available seeds in the correct order."""
    print("🌱 Running all database seeds...")
    
    # Order matters: users first, then agents that might reference users
    seed_mock_users(session)
    seed_agent_templates(session)
    
    print("✅ All seeds completed!")
