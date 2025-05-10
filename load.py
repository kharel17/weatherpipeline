import os
import csv
import sqlite3
import pandas as pd
from datetime import datetime

def save_to_csv(data, filename=None):
    try:
        os.makedirs('data', exist_ok=True)
        if not filename:
            current_date = datetime.now().strftime('%Y-%m-%d')
            filename = f'weather_data_{current_date}.csv'
        filepath = os.path.join('data', filename)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        df.to_csv(filepath, index=False)
        print(f"[INFO] Data successfully saved to {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Failed to save data to CSV: {e}")
        return None

def save_to_sqlite(data, db_name='weather_data.db'):
    try:
        os.makedirs('data', exist_ok=True)
        db_path = os.path.join('data', db_name)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        conn = sqlite3.connect(db_path)
        df.to_sql('weather_data', conn, if_exists='append', index=False)
        conn.close()
        print(f"[INFO] Data successfully saved to SQLite database: {db_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save data to SQLite: {e}")
        return False

def create_sqlite_tables(db_name='weather_data.db'):
    try:
        os.makedirs('data', exist_ok=True)
        db_path = os.path.join('data', db_name)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
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
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_date ON weather_data (date)
        ''')
        conn.commit()
        conn.close()
        print(f"[INFO] SQLite database initialized: {db_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to initialize SQLite database: {e}")
        return False

def query_latest_data(db_name='weather_data.db', limit=5):
    try:
        db_path = os.path.join('data', db_name)
        if not os.path.exists(db_path):
            print(f"[WARNING] Database {db_path} does not exist.")
            return pd.DataFrame()
        conn = sqlite3.connect(db_path)
        query = f"SELECT * FROM weather_data ORDER BY date DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"[ERROR] Failed to query data from SQLite: {e}")
        return pd.DataFrame()
