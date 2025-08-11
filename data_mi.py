    # database_migration.py
"""
Database migration script to fix schema issues in Weather Insight Engine
Adds missing pipeline_version column to data_quality_log table
"""

import sqlite3
import os
from datetime import datetime, UTC
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_database(db_path):
    """Create a backup of the database before migration"""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        # Copy database file
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns

def migrate_database(db_path):
    """Perform database migration"""
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    # Create backup first
    backup_path = backup_database(db_path)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if pipeline_version column exists
        if not check_column_exists(cursor, 'data_quality_log', 'pipeline_version'):
            logger.info("Adding pipeline_version column to data_quality_log table...")
            
            # Add the missing column with a default value
            cursor.execute("""
                ALTER TABLE data_quality_log 
                ADD COLUMN pipeline_version TEXT DEFAULT 'v1.0'
            """)
            
            # Update any existing records with the default version
            cursor.execute("""
                UPDATE data_quality_log 
                SET pipeline_version = 'v1.0' 
                WHERE pipeline_version IS NULL
            """)
            
            conn.commit()
            logger.info("Successfully added pipeline_version column")
        else:
            logger.info("pipeline_version column already exists - skipping migration")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM data_quality_log")
        total_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM data_quality_log WHERE pipeline_version IS NOT NULL")
        updated_records = cursor.fetchone()[0]
        
        logger.info(f"Migration verification: {updated_records}/{total_records} records have pipeline_version")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database migration failed: {e}")
        logger.info(f"Database backup available at: {backup_path}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return False


def main():
    """Main migration function"""
    # Default database path
    db_path = "data/weather_data.db"
    
    # Check if custom path provided
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    logger.info(f"Starting database migration for: {db_path}")
    
    if migrate_database(db_path):
        logger.info("Database migration completed successfully!")
        return 0
    else:
        logger.error("Database migration failed!")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)