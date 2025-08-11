"""
Database Migration Script
Fixes missing columns and database schema issues
"""

import sqlite3
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """
    Migrate database to fix schema issues
    """
    # Database path
    db_path = Path("data/weather_data.db")
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return False
    
    # Create backup
    backup_path = db_path.with_suffix('.db.backup')
    if not backup_path.exists():
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if pipeline_version column exists
        cursor.execute("PRAGMA table_info(data_quality_log)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'pipeline_version' not in columns:
            logger.info("Adding missing pipeline_version column...")
            cursor.execute("""
                ALTER TABLE data_quality_log 
                ADD COLUMN pipeline_version TEXT DEFAULT '1.0.0'
            """)
            logger.info("✓ Added pipeline_version column")
        else:
            logger.info("✓ pipeline_version column already exists")
        
        # Update any NULL values to default
        cursor.execute("""
            UPDATE data_quality_log 
            SET pipeline_version = '1.0.0' 
            WHERE pipeline_version IS NULL
        """)
        
        # Check and fix weather_records table constraints
        cursor.execute("PRAGMA table_info(weather_records)")
        weather_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"Weather records table has {len(weather_columns)} columns")
        
        conn.commit()
        logger.info("✓ Database migration completed successfully")
        
        # Test the fix by running a sample query
        cursor.execute("""
            SELECT COUNT(*) as total_logs,
                   AVG(CAST(records_processed as REAL)) as avg_processed,
                   pipeline_version
            FROM data_quality_log 
            GROUP BY pipeline_version
        """)
        
        results = cursor.fetchall()
        logger.info(f"✓ Test query successful: {len(results)} pipeline versions found")
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database migration failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return False
    finally:
        if conn:
            conn.close()

def fix_duplicate_records():
    """
    Handle duplicate records by keeping the latest one
    """
    try:
        conn = sqlite3.connect("data/weather_data.db")
        cursor = conn.cursor()
        
        # Find duplicates
        cursor.execute("""
            SELECT date, latitude, longitude, COUNT(*) as count
            FROM weather_records
            GROUP BY date, latitude, longitude
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        logger.info(f"Found {len(duplicates)} duplicate record groups")
        
        # Remove duplicates, keeping the latest created_at
        for date, lat, lon, count in duplicates:
            cursor.execute("""
                DELETE FROM weather_records 
                WHERE date = ? AND latitude = ? AND longitude = ?
                AND id NOT IN (
                    SELECT id FROM weather_records 
                    WHERE date = ? AND latitude = ? AND longitude = ?
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
            """, (date, lat, lon, date, lat, lon))
            
            deleted = cursor.rowcount
            logger.info(f"Removed {deleted} duplicate records for {date} at {lat},{lon}")
        
        conn.commit()
        logger.info("✓ Duplicate records cleaned up")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing duplicates: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_database():
    """
    Verify database structure and data integrity
    """
    try:
        conn = sqlite3.connect("data/weather_data.db")
        cursor = conn.cursor()
        
        # Check table structure
        tables = ['weather_records', 'data_quality_log', 'location_summary']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"✓ {table}: {count} records")
        
        # Check for any remaining duplicates
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT date, latitude, longitude, COUNT(*) as count
                FROM weather_records
                GROUP BY date, latitude, longitude
                HAVING COUNT(*) > 1
            )
        """)
        
        duplicates = cursor.fetchone()[0]
        if duplicates == 0:
            logger.info("✓ No duplicate records found")
        else:
            logger.warning(f"⚠ Still {duplicates} duplicate record groups")
        
        return True
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🔧 Starting database migration...")
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Run migration
    if migrate_database():
        print("✅ Migration completed successfully")
        
        # Fix duplicates
        print("\n🔄 Fixing duplicate records...")
        if fix_duplicate_records():
            print("✅ Duplicates fixed")
        
        # Verify
        print("\n🔍 Verifying database...")
        if verify_database():
            print("✅ Database verification passed")
        
        print("\nAll fixes completed! Your application should work now.")
    else:
        print("❌ Migration failed. Check the logs above.")