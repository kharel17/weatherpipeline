"""
Fix Database Issues - Simple Solution
Clear existing data to avoid duplicate record conflicts
"""

import sqlite3
import os
from pathlib import Path

def clear_database():
    """Clear the existing database to avoid duplicate record issues"""
    
    db_path = Path("data/weather_data.db")
    
    print("🔧 FIXING DATABASE ISSUES")
    print("=" * 40)
    
    if not db_path.exists():
        print("✅ No existing database found - this is perfect!")
        print("A fresh database will be created when you run the ETL.")
        return True
    
    try:
        print(f"Found existing database: {db_path}")
        
        # Connect and check what's in there
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if weather_records table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_records'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Count existing records
            cursor.execute("SELECT COUNT(*) FROM weather_records")
            record_count = cursor.fetchone()[0]
            print(f"Found {record_count} existing weather records")
            
            # Clear the table to avoid duplicates
            cursor.execute("DELETE FROM weather_records")
            print("✅ Cleared all existing weather records")
        else:
            print("No weather_records table found - this is fine")
        
        conn.commit()
        conn.close()
        
        print("✅ Database prepared successfully")
        print("\nNext step: Run debug_etl.py again")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False

if __name__ == "__main__":
    success = clear_database()
    
    if success:
        print("\n" + "=" * 40)
        print("🎉 DATABASE FIXED!")
        print("Now run: python debug_etl.py")
    else:
        print("\n❌ Failed to fix database")