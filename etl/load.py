"""
Enhanced Weather Data Loader
Improved version with better error handling, duplicate record handling, and multiple export formats
"""

import os
import csv
import sqlite3
import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class WeatherLoader:
    """
    Enhanced weather data loader with multiple storage options and improved error handling
    """
    
    def __init__(self, data: Union[List[Dict], pd.DataFrame], data_dir: str = "data"):
        """
        Initialize the weather data loader
        
        Args:
            data: Weather data to load (list of dicts or DataFrame)
            data_dir: Directory for data storage
        """
        self.data = pd.DataFrame(data) if isinstance(data, list) else data
        self.data_dir = Path(data_dir)
        self.csv_dir = self.data_dir / "csv_exports"
        self.json_dir = self.data_dir / "json_exports"
        
        # Create directories if they don't exist
        for directory in [self.data_dir, self.csv_dir, self.json_dir]:
            directory.mkdir(exist_ok=True)
            
        logger.info(f"WeatherLoader initialized with {len(self.data)} records")

    def save_to_csv(self, filename: Optional[str] = None, include_metadata: bool = True) -> Optional[str]:
        """
        Save data to CSV file with enhanced metadata
        
        Args:
            filename: Custom filename (optional)
            include_metadata: Include metadata header in CSV
            
        Returns:
            str: Path to saved file or None if failed
        """
        try:
            if self.data.empty:
                logger.warning("No data to save to CSV")
                return None
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                location_info = self._get_location_identifier()
                filename = f'weather_data_{location_info}_{timestamp}.csv'
            
            filepath = self.csv_dir / filename
            
            # Save with metadata header if requested
            if include_metadata:
                self._save_csv_with_metadata(filepath)
            else:
                self.data.to_csv(filepath, index=False)
            
            logger.info(f"Data successfully saved to CSV: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save data to CSV: {e}")
            return None

    def save_to_json(self, filename: Optional[str] = None, include_metadata: bool = True) -> Optional[str]:
        """
        Save data to JSON file with metadata
        
        Args:
            filename: Custom filename (optional)
            include_metadata: Include metadata in JSON
            
        Returns:
            str: Path to saved file or None if failed
        """
        try:
            if self.data.empty:
                logger.warning("No data to save to JSON")
                return None
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                location_info = self._get_location_identifier()
                filename = f'weather_data_{location_info}_{timestamp}.json'
            
            filepath = self.json_dir / filename
            
            # Prepare data for JSON export
            json_data = {
                "metadata": self._generate_metadata() if include_metadata else {},
                "data": self.data.to_dict('records')
            }
            
            # Save to JSON with proper formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"Data successfully saved to JSON: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save data to JSON: {e}")
            return None

    def save_to_sqlite(self, db_name: str = 'weather_data.db', table_name: str = 'weather_records') -> bool:
        """
        Save data to SQLite database with improved duplicate handling
        
        Args:
            db_name: Database filename
            table_name: Table name for weather data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.data.empty:
                logger.warning("No data to save to SQLite")
                return False
            
            db_path = self.data_dir / db_name
            
            # Create connection with proper error handling
            with sqlite3.connect(db_path) as conn:
                # Enable foreign keys and other optimizations
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                
                cursor = conn.cursor()
                
                # Process each record individually to handle duplicates
                inserted_count = 0
                updated_count = 0
                
                for _, record in self.data.iterrows():
                    try:
                        # Try to insert the record first
                        self._insert_record(cursor, record, table_name)
                        inserted_count += 1
                        
                    except sqlite3.IntegrityError as e:
                        if "UNIQUE constraint failed" in str(e):
                            # Record exists, update it instead
                            if self._update_record(cursor, record, table_name):
                                updated_count += 1
                                logger.debug(f"Updated existing record for {record.get('date')} at {record.get('latitude')}, {record.get('longitude')}")
                            else:
                                logger.warning(f"Failed to update record for {record.get('date')}")
                        else:
                            # Different integrity error - re-raise
                            logger.error(f"Integrity error: {e}")
                            raise e
                
                conn.commit()
                
                total_processed = inserted_count + updated_count
                logger.info(f"Successfully processed {total_processed} records to SQLite: {db_path}")
                logger.info(f"  - Inserted: {inserted_count} new records")
                logger.info(f"  - Updated: {updated_count} existing records")
                
                return total_processed > 0
                
        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to save data to SQLite: {e}")
            return False

    def _insert_record(self, cursor: sqlite3.Cursor, record: pd.Series, table_name: str) -> None:
        """
        Insert a single record into the database
        
        Args:
            cursor: Database cursor
            record: Single record to insert
            table_name: Target table name
        """
        # Define the column mapping
        columns = [
            'date', 'latitude', 'longitude', 'timezone', 'elevation',
            'current_temp_c', 'current_condition', 'wind_kph', 'wind_dir',
            'forecast_max_temp', 'forecast_min_temp', 'precipitation_mm', 
            'uv_index', 'weather_code', 'forecast_condition',
            'pm2_5', 'pm10', 'us_aqi', 'european_aqi', 'aqi_category',
            'measurement_time', 'last_updated', 'created_at', 'data_source'
        ]
        
        # Prepare values (handle missing columns)
        values = []
        for col in columns:
            if col in record.index:
                value = record[col]
                # Handle NaN values
                if pd.isna(value):
                    values.append(None)
                else:
                    values.append(value)
            else:
                # Provide defaults for missing columns
                if col == 'created_at':
                    values.append(datetime.now().isoformat())
                elif col == 'data_source':
                    values.append('open-meteo')
                else:
                    values.append(None)
        
        # Create the INSERT SQL
        placeholders = ', '.join(['?' for _ in columns])
        column_names = ', '.join(columns)
        
        sql = f"""
            INSERT INTO {table_name} 
            ({column_names})
            VALUES ({placeholders})
        """
        
        cursor.execute(sql, values)

    def _update_record(self, cursor: sqlite3.Cursor, record: pd.Series, table_name: str) -> bool:
        """
        Update an existing record in the database
        
        Args:
            cursor: Database cursor
            record: Record data to update
            table_name: Target table name
            
        Returns:
            bool: True if update was successful
        """
        try:
            # Define updatable columns (excluding key columns and timestamps)
            update_columns = [
                'current_temp_c', 'current_condition', 'wind_kph', 'wind_dir',
                'forecast_max_temp', 'forecast_min_temp', 'precipitation_mm',
                'uv_index', 'weather_code', 'forecast_condition',
                'pm2_5', 'pm10', 'us_aqi', 'european_aqi', 'aqi_category',
                'timezone', 'elevation', 'measurement_time'
            ]
            
            # Build SET clause
            set_clauses = []
            values = []
            
            for col in update_columns:
                if col in record.index:
                    set_clauses.append(f"{col} = ?")
                    value = record[col]
                    values.append(None if pd.isna(value) else value)
            
            # Add last_updated timestamp
            set_clauses.append("last_updated = ?")
            values.append(datetime.now().isoformat())
            
            # Add WHERE clause values
            values.extend([record['date'], record['latitude'], record['longitude']])
            
            sql = f"""
                UPDATE {table_name} 
                SET {', '.join(set_clauses)}
                WHERE date = ? AND latitude = ? AND longitude = ?
            """
            
            cursor.execute(sql, values)
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to update record: {e}")
            return False

    def save_all_formats(self, base_filename: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Save data in all supported formats
        
        Args:
            base_filename: Base filename (without extension)
            
        Returns:
            Dict: Paths to saved files for each format
        """
        if not base_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            location_info = self._get_location_identifier()
            base_filename = f'weather_data_{location_info}_{timestamp}'
        
        results = {}
        
        # Save in each format
        results['csv'] = self.save_to_csv(f"{base_filename}.csv")
        results['json'] = self.save_to_json(f"{base_filename}.json")
        results['sqlite'] = self.save_to_sqlite()
        
        # Summary
        successful = sum(1 for v in results.values() if v is not None and v is not False)
        logger.info(f"Saved data in {successful}/3 formats successfully")
        
        return results

    @staticmethod
    def create_sqlite_tables(db_name: str = 'weather_data.db', data_dir: str = "data") -> bool:
        """
        Create SQLite database tables with enhanced schema
        
        Args:
            db_name: Database filename
            data_dir: Directory for database storage
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data_path = Path(data_dir)
            data_path.mkdir(exist_ok=True)
            db_path = data_path / db_name
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Create main weather records table with enhanced schema
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS weather_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        
                        -- Temporal data
                        date TEXT NOT NULL,
                        last_updated TEXT,
                        measurement_time TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        
                        -- Location data
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        timezone TEXT,
                        elevation REAL,
                        
                        -- Current weather
                        current_temp_c REAL,
                        current_condition TEXT,
                        wind_kph REAL,
                        wind_dir TEXT,
                        
                        -- Daily forecast
                        forecast_max_temp REAL,
                        forecast_min_temp REAL,
                        precipitation_mm REAL,
                        uv_index REAL,
                        weather_code INTEGER,
                        forecast_condition TEXT,
                        
                        -- Air quality
                        pm2_5 REAL,
                        pm10 REAL,
                        us_aqi INTEGER,
                        european_aqi INTEGER,
                        aqi_category TEXT,
                        
                        -- Metadata
                        data_source TEXT DEFAULT 'open-meteo',
                        
                        -- Constraints
                        UNIQUE(date, latitude, longitude)
                    )
                ''')
                
                # Create indexes for better query performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_date ON weather_records (date)",
                    "CREATE INDEX IF NOT EXISTS idx_location ON weather_records (latitude, longitude)",
                    "CREATE INDEX IF NOT EXISTS idx_date_location ON weather_records (date, latitude, longitude)",
                    "CREATE INDEX IF NOT EXISTS idx_created_at ON weather_records (created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_aqi ON weather_records (us_aqi)"
                ]
                
                for index_sql in indexes:
                    cursor.execute(index_sql)
                
                # Create data quality summary table with pipeline_version column
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS data_quality_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        records_processed INTEGER,
                        records_saved INTEGER,
                        errors_count INTEGER,
                        processing_time_seconds REAL,
                        location_lat REAL,
                        location_lon REAL,
                        notes TEXT,
                        pipeline_version TEXT DEFAULT '1.0.0'
                    )
                ''')
                
                conn.commit()
                logger.info(f"SQLite database and tables created successfully: {db_path}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"SQLite error creating tables: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create SQLite tables: {e}")
            return False

    @staticmethod
    def query_latest_data(db_name: str = 'weather_data.db', data_dir: str = "data", 
                         limit: int = 10, location_filter: Optional[tuple] = None) -> pd.DataFrame:
        """
        Query latest weather data from database with optional location filtering
        
        Args:
            db_name: Database filename
            data_dir: Directory containing database
            limit: Maximum number of records to return
            location_filter: Tuple of (lat, lon) to filter by location
            
        Returns:
            pd.DataFrame: Latest weather records
        """
        try:
            db_path = Path(data_dir) / db_name
            
            if not db_path.exists():
                logger.warning(f"Database {db_path} does not exist")
                return pd.DataFrame()
            
            with sqlite3.connect(db_path) as conn:
                # Build query with optional location filter
                query = "SELECT * FROM weather_records"
                params = []
                
                if location_filter:
                    lat, lon = location_filter
                    tolerance = 0.01  # Small tolerance for floating point comparison
                    query += " WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
                    params.extend([lat - tolerance, lat + tolerance, lon - tolerance, lon + tolerance])
                
                query += " ORDER BY date DESC, created_at DESC LIMIT ?"
                params.append(limit)
                
                df = pd.read_sql_query(query, conn, params=params)
                logger.info(f"Retrieved {len(df)} records from database")
                return df
                
        except sqlite3.Error as e:
            logger.error(f"SQLite error querying data: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to query data from SQLite: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_database_stats(db_name: str = 'weather_data.db', data_dir: str = "data") -> Dict[str, Any]:
        """
        Get statistics about the database
        
        Args:
            db_name: Database filename
            data_dir: Directory containing database
            
        Returns:
            Dict: Database statistics
        """
        try:
            db_path = Path(data_dir) / db_name
            
            if not db_path.exists():
                return {"error": "Database does not exist"}
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Get basic stats
                cursor.execute("SELECT COUNT(*) FROM weather_records")
                total_records = cursor.fetchone()[0]
                
                cursor.execute("SELECT MIN(date), MAX(date) FROM weather_records")
                date_range = cursor.fetchone()
                
                cursor.execute("SELECT COUNT(DISTINCT latitude || ',' || longitude) FROM weather_records")
                unique_locations = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM weather_records WHERE created_at >= date('now', '-1 day')")
                records_last_24h = cursor.fetchone()[0]
                
                # Get database file size
                file_size_mb = db_path.stat().st_size / (1024 * 1024)
                
                return {
                    "total_records": total_records,
                    "date_range": {
                        "earliest": date_range[0],
                        "latest": date_range[1]
                    },
                    "unique_locations": unique_locations,
                    "records_last_24h": records_last_24h,
                    "database_size_mb": round(file_size_mb, 2),
                    "last_updated": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}

    def _save_csv_with_metadata(self, filepath: Path) -> None:
        """Save CSV file with metadata header"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            # Write metadata header as comments
            metadata = self._generate_metadata()
            for key, value in metadata.items():
                f.write(f"# {key}: {value}\n")
            f.write("#\n")
            
            # Write CSV data
            self.data.to_csv(f, index=False)

    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate metadata for the dataset"""
        if self.data.empty:
            return {}
        
        return {
            "generated_at": datetime.now().isoformat(),
            "total_records": len(self.data),
            "date_range": f"{self.data['date'].min()} to {self.data['date'].max()}",
            "locations": f"{self.data['latitude'].nunique()} unique location(s)",
            "data_source": self.data.get('data_source', ['unknown']).iloc[0] if 'data_source' in self.data.columns else 'unknown',
            "format_version": "1.0",
            "columns": list(self.data.columns)
        }

    def _get_location_identifier(self) -> str:
        """Get a string identifier for the location(s) in the dataset"""
        if self.data.empty:
            return "unknown"
        
        unique_locations = self.data[['latitude', 'longitude']].drop_duplicates()
        if len(unique_locations) == 1:
            lat = unique_locations.iloc[0]['latitude']
            lon = unique_locations.iloc[0]['longitude']
            return f"lat{lat:.2f}_lon{lon:.2f}"
        else:
            return f"multi_location_{len(unique_locations)}sites"

    def log_data_quality(self, processing_time: float, errors_count: int = 0, notes: str = "") -> None:
        """
        Log data quality metrics to database
        
        Args:
            processing_time: Time taken to process data
            errors_count: Number of errors encountered
            notes: Additional notes
        """
        try:
            if self.data.empty:
                return
            
            # Get representative location
            lat = self.data['latitude'].iloc[0] if 'latitude' in self.data.columns else None
            lon = self.data['longitude'].iloc[0] if 'longitude' in self.data.columns else None
            
            db_path = self.data_dir / 'weather_data.db'
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO data_quality_log 
                    (records_processed, records_saved, errors_count, processing_time_seconds, 
                     location_lat, location_lon, notes, pipeline_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    len(self.data), len(self.data), errors_count, processing_time,
                    lat, lon, notes, '1.0.0'
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log data quality metrics: {e}")