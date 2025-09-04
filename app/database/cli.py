#!/usr/bin/env python3
"""
Database management CLI for IPRE Debate Agents application.

Usage:
    python -m app.database.cli migrate    # Run pending migrations  
    python -m app.database.cli reset      # Drop all tables and recreate
    python -m app.database.cli seed       # Seed database with initial data
    python -m app.database.cli fresh      # Drop, recreate, and seed
"""

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlmodel import Session, create_engine, SQLModel, text
from alembic import command
from alembic.config import Config as AlembicConfig
from app.database.seeds import run_all_seeds, seed_agent_templates, seed_mock_users

# Database connection - match the main.py database URL  
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://ipre_user:ipre_password@localhost:5432/ipre_db")
engine = create_engine(DATABASE_URL)

# Alembic configuration
alembic_cfg = AlembicConfig("alembic.ini")


def migrate():
    """Run pending migrations (equivalent to 'alembic upgrade head')."""
    print("Running database migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


def drop_all_tables():
    """Drop all tables in the database."""
    print("Dropping all tables...")
    try:
        # For SQLModel/SQLAlchemy, we can drop all tables
        SQLModel.metadata.drop_all(engine)
        print("✅ All tables dropped successfully!")
    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")
        sys.exit(1)


def create_all_tables():
    """Create all tables based on SQLModel definitions."""
    print("Creating all tables...")
    try:
        SQLModel.metadata.create_all(engine)
        print("✅ All tables created successfully!")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        sys.exit(1)


def reset_database():
    """Drop all tables and recreate them (fresh schema)."""
    print("Resetting database (drop + create)...")
    drop_all_tables()
    create_all_tables()
    print("✅ Database reset completed!")


def seed_database_cli():
    """Seed the database with initial data."""
    print("🌱 Seeding database...")
    try:
        with Session(engine) as session:
            run_all_seeds(session)
        print("✅ Database seeding completed!")
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        sys.exit(1)


def seed_agents_only():
    """Seed only agent templates."""
    print("🌱 Seeding agent templates...")
    try:
        with Session(engine) as session:
            seed_agent_templates(session)
        print("✅ Agent seeding completed!")
    except Exception as e:
        print(f"❌ Agent seeding failed: {e}")
        sys.exit(1)


def seed_users_only():
    """Seed only users."""
    print("🌱 Seeding users...")
    try:
        with Session(engine) as session:
            seed_mock_users(session)
        print("✅ User seeding completed!")
    except Exception as e:
        print(f"❌ User seeding failed: {e}")
        sys.exit(1)


def fresh_database():
    """Drop, recreate, and seed the database (reset + seed)."""
    print("Refreshing database (reset + seed)...")
    reset_database()
    seed_database_cli()
    print("✅ Database refresh completed!")


def show_migration_status():
    """Show the current migration status."""
    print("Migration status:")
    try:
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        
        # Get current revision from database
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
        
        # Get available migrations
        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()
        
        print(f"Current revision: {current_rev or 'None'}")
        print(f"Head revision: {head_rev}")
        
        if current_rev == head_rev:
            print("✅ Database is up to date!")
        else:
            print("⚠️  Database needs migration!")
            
    except Exception as e:
        print(f"❌ Failed to check migration status: {e}")


def rollback_migration():
    """Rollback the last migration."""
    print("Rolling back last migration...")
    try:
        command.downgrade(alembic_cfg, "-1")
        print("✅ Rollback completed!")
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        sys.exit(1)


def show_tables():
    """Show all tables in the database."""
    print("Tables in database:")
    try:
        with Session(engine) as session:
            # Query for table names (PostgreSQL specific)
            result = session.exec(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            tables = result.fetchall()
            
            if tables:
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("  No tables found.")
                
    except Exception as e:
        print(f"❌ Failed to list tables: {e}")


def test_connection():
    """Test database connection."""
    print("Testing database connection...")
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Database management CLI for IPRE Debate Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/db.py migrate     # Run migrations
  python scripts/db.py fresh       # Reset and seed database
  python scripts/db.py status      # Check migration status
        """
    )
    
    parser.add_argument(
        "command",
        choices=[
            "migrate", "reset", "seed", "drop", "fresh", 
            "status", "rollback", "tables", "test",
            "seed-agents", "seed-users"
        ],
        help="Database command to run"
    )
    
    args = parser.parse_args()
    
    # Command mapping
    commands = {
        "migrate": migrate,
        "reset": reset_database,
        "seed": seed_database_cli,
        "seed-agents": seed_agents_only,
        "seed-users": seed_users_only,
        "drop": drop_all_tables,
        "fresh": fresh_database,
        "status": show_migration_status,
        "rollback": rollback_migration,
        "tables": show_tables,
        "test": test_connection,
    }
    
    # Execute the command
    print(f"🚀 Executing: db {args.command}")
    print("-" * 50)
    commands[args.command]()


if __name__ == "__main__":
    main()
