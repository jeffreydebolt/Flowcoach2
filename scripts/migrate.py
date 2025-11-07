#!/usr/bin/env python3
"""Database migration runner for FlowCoach."""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from apps
sys.path.insert(0, str(Path(__file__).parent.parent))

# Bootstrap environment variables in local mode
from apps.server.core.env_bootstrap import bootstrap_env
bootstrap_env()

from apps.server.db.engine import get_db


def run_migrations():
    """Run database migrations."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Get database engine
        db_engine = get_db()
        logger.info(f"Running migrations for {db_engine.driver_name} database")

        # Get migrations directory
        migrations_dir = Path(__file__).parent.parent / 'apps' / 'server' / 'db' / 'migrations'

        if not migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {migrations_dir}")
            return

        # Get migration files
        migration_files = sorted(migrations_dir.glob('*.sql'))

        if not migration_files:
            logger.info("No migration files found")
            return

        # Run each migration
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")

            try:
                with open(migration_file, 'r') as f:
                    migration_sql = f.read()

                # Skip empty migrations
                if not migration_sql.strip():
                    logger.info(f"Skipping empty migration: {migration_file.name}")
                    continue

                # Execute migration
                db_engine.execute_migration(migration_sql)
                logger.info(f"Successfully applied migration: {migration_file.name}")

            except Exception as e:
                logger.error(f"Failed to apply migration {migration_file.name}: {e}")
                raise

        logger.info("All migrations completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
