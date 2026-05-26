#!/usr/bin/env python3
"""Database migration runner."""
import sys
from pathlib import Path

import psycopg

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings

settings = get_settings()


def run_migrations():
    """Run all SQL migration files in order."""
    migrations_dir = Path(__file__).parent
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("No migration files found.")
        return
    
    print(f"Found {len(migration_files)} migration file(s)")
    
    try:
        with psycopg.connect(settings.database_url) as conn:
            for migration_file in migration_files:
                print(f"Running migration: {migration_file.name}")
                sql = migration_file.read_text()
                conn.execute(sql)
                conn.commit()
                print(f"✓ {migration_file.name} completed")
        
        print("\n✓ All migrations completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
