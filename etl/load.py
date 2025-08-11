import os
import csv
import sqlite3
import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import WeatherRecord, Base

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

    def save_to_sqlite(self, db_url: str, table_name: str = 'weather_records', replace: bool = False) -> bool:
        """
        Save data to SQLite database using SQLAlchemy session
        
        Args:
            db_url: Database connection URL (e.g., sqlite:///path/to/db)
            table_name: Table name for weather data (should be 'weather_records')
            replace: If True, replace existing records with matching date, latitude, longitude
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.data.empty:
                logger.warning("No data to save to SQLite")
                return False
            
            # Create a new engine and session for this operation
            engine = create_engine(db_url)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            Base.metadata.create_all(engine)  # Ensure tables exist
            
            for record in self.data.to_dict('records'):
                # Convert string DateTime fields to datetime objects
                for field in ['last_updated', 'measurement_time', 'created_at']:
                    if field in record and isinstance(record[field], str):
                        try:
                            record[field] = datetime.fromisoformat(record[field].replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            record[field] = datetime.utcnow() if field == 'created_at' else None
                
                existing = session.query(WeatherRecord).filter_by(
                    date=record['date'],
                    latitude=record['latitude'],
                    longitude=record['longitude']
                ).first()
                if existing and replace:
                    # Update existing record
                    for key, value in record.items():
                        setattr(existing, key, value)
                elif not existing:
                    # Add new record
                    session.add(WeatherRecord.from_dict(record))
            
            session.commit()
            logger.info(f"Successfully saved {len(self.data)} records to {table_name}")
            session.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save data to {table_name}: {e}")
            session.rollback()
            session.close()
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
        results['sqlite'] = self.save_to_sqlite(f"sqlite:///{self.data_dir / 'weather_data.db'}")
        
        # Summary
        successful = sum(1 for v in results.values() if v is not None and v is not False)
        logger.info(f"Saved data in {successful}/3 formats successfully")
        
        return results

    @staticmethod
    def create_sqlite_tables(db_name: str = 'weather_data.db', data_dir: str = "data") -> bool:
        """
        Create SQLite database tables based on SQLAlchemy models
        
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
            
            # Use SQLAlchemy to create tables based on models
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(engine)
            logger.info(f"SQLite database and tables created successfully: {db_path}")
            return True
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
                     location_lat, location_lon, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    len(self.data), len(self.data), errors_count, processing_time,
                    lat, lon, notes
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log data quality metrics: {e}")