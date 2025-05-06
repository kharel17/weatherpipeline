"""
load.py - Load module for Weather Data Pipeline

This script handles the loading/saving of transformed weather data.
It provides functions to save data as CSV files or into a SQLite database.

Author: Your Name
Date: May 5, 2025
"""

import os
import csv
import sqlite3
import pandas as pd
from datetime import datetime


def save_to_csv(data, filename=None):
    """
    Save transformed weather data to a CSV file.
    
    Args:
        data (list or pandas.DataFrame): Transformed weather data
        filename (str, optional): Custom filename, defaults to 'weather_data_YYYY-MM-DD.csv'
        
    Returns:
        str: Path to the saved CSV file
    """
    try:
        # Create 'data' directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Generate default filename if none provided
        if not filename:
            current_date = datetime.now().strftime('%Y-%m-%d')
            filename = f'weather_data_{current_date}.csv'
        
        # Ensure the path includes the data directory
        filepath = os.path.join('data', filename)
        
        # Convert to DataFrame if it's a list
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
            
        # Save to CSV
        df.to_csv(filepath, index=False)
        
        print(f"[INFO] Data successfully saved to {filepath}")
        return filepath
    
    except Exception as e:
        print(f"[ERROR] Failed to save data to CSV: {e}")
        return None


def save_to_sqlite(data, db_name='weather_data.db'):
    """
    Save transformed weather data to a SQLite database.
    
    Args:
        data (list or pandas.DataFrame): Transformed weather data
        db_name (str, optional): Database filename, defaults to 'weather_data.db'
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create 'data' directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Ensure the path includes the data directory
        db_path = os.path.join('data', db_name)
        
        # Convert to DataFrame if it's a list
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
            
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        
        # Save to SQLite
        df.to_sql('weather_data', conn, if_exists='append', index=False)
        
        # Close connection
        conn.close()
        
        print(f"[INFO] Data successfully saved to SQLite database: {db_path}")
        return True
    
    except Exception as e:
        print(f"[ERROR] Failed to save data to SQLite: {e}")
        return False


def create_sqlite_tables(db_name='weather_data.db'):
    """
    Create SQLite database tables if they don't exist.
    
    Args:
        db_name (str, optional): Database filename, defaults to 'weather_data.db'
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create 'data' directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Ensure the path includes the data directory
        db_path = os.path.join('data', db_name)
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            date TEXT,
            latitude REAL,
            longitude REAL,
            timezone TEXT,
            last_updated TEXT,
            current_temp_c REAL,
            current_condition TEXT,
            wind_kph REAL,
            wind_dir TEXT,
            pm2_5 REAL,
            pm10 REAL,
            us_aqi INTEGER,
            aqi_category TEXT,
            forecast_max_temp REAL,
            forecast_min_temp REAL,
            precipitation_mm REAL,
            uv_index REAL
        )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_date ON weather_data (date)
        ''')
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print(f"[INFO] SQLite database initialized: {db_path}")
        return True
    
    except Exception as e:
        print(f"[ERROR] Failed to initialize SQLite database: {e}")
        return False


def query_latest_data(db_name='weather_data.db', limit=5):
    """
    Query the latest records from the SQLite database.
    
    Args:
        db_name (str, optional): Database filename, defaults to 'weather_data.db'
        limit (int, optional): Maximum number of records to return, defaults to 5
        
    Returns:
        pandas.DataFrame: Latest weather data records
    """
    try:
        # Ensure the path includes the data directory
        db_path = os.path.join('data', db_name)
        
        # Check if database exists
        if not os.path.exists(db_path):
            print(f"[WARNING] Database {db_path} does not exist.")
            return pd.DataFrame()
            
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        
        # Query latest records
        query = f"SELECT * FROM weather_data ORDER BY date DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        
        # Close connection
        conn.close()
        
        return df
    
    except Exception as e:
        print(f"[ERROR] Failed to query data from SQLite: {e}")
        return pd.DataFrame()


# Example usage (uncomment for testing)
"""
if __name__ == "__main__":
    # Import modules for testing
    import extract
    import transform
    
    # Define location
    LAT = 27.7  # Kathmandu Latitude
    LON = 85.3  # Kathmandu Longitude
    
    # Fetch and transform data
    weather_data = extract.fetch_weather_forecast(LAT, LON)
    air_data = extract.fetch_air_quality(LAT, LON)
    transformed_data = transform.transform_weather_data(weather_data, air_data)
    
    # Initialize SQLite database
    create_sqlite_tables()
    
    # Save data to CSV and SQLite
    csv_path = save_to_csv(transformed_data)
    db_success = save_to_sqlite(transformed_data)
    
    # Query and display latest data
    latest_data = query_latest_data(limit=3)
    print("\n----- LATEST DATA FROM DATABASE -----")
    print(latest_data)
"""