"""
Database Models for Weather Insight Engine
SQLAlchemy models for weather data management
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

# SQLAlchemy base
Base = declarative_base()

# Global database session
db_session = None
engine = None


class QueryProperty:
    """Property that provides query functionality to SQLAlchemy models"""
    def __init__(self, session):
        self.session = session
    
    def __get__(self, obj, cls):
        if obj is not None:
            return obj
        return self.session.query(cls)


class WeatherRecord(Base):
    """
    Main weather record model
    Stores weather forecast and air quality data for specific locations and dates
    """
    __tablename__ = 'weather_records'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Temporal data
    date = Column(String(10), nullable=False, index=True)  # Format: YYYY-MM-DD
    last_updated = Column(DateTime, default=datetime.utcnow)
    measurement_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Location data
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    timezone = Column(String(100))
    elevation = Column(Float, default=0.0)
    
    # Current weather conditions
    current_temp_c = Column(Float)
    current_condition = Column(String(100))
    wind_kph = Column(Float)
    wind_dir = Column(String(10))
    
    # Daily forecast data
    forecast_max_temp = Column(Float)
    forecast_min_temp = Column(Float)
    precipitation_mm = Column(Float, default=0.0)
    uv_index = Column(Float)
    weather_code = Column(Integer)
    forecast_condition = Column(String(100))
    
    # Air quality data
    pm2_5 = Column(Float)
    pm10 = Column(Float)
    us_aqi = Column(Integer)
    european_aqi = Column(Integer)
    aqi_category = Column(String(50))
    
    # Metadata
    data_source = Column(String(50), default='open-meteo')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('date', 'latitude', 'longitude', name='_date_location_uc'),
        Index('idx_location', 'latitude', 'longitude'),
        Index('idx_date_location', 'date', 'latitude', 'longitude'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<WeatherRecord(date='{self.date}', lat={self.latitude}, lon={self.longitude})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary"""
        return {
            'id': self.id,
            'date': self.date,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'measurement_time': self.measurement_time.isoformat() if self.measurement_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'timezone': self.timezone,
            'elevation': self.elevation,
            'current_temp_c': self.current_temp_c,
            'current_condition': self.current_condition,
            'wind_kph': self.wind_kph,
            'wind_dir': self.wind_dir,
            'forecast_max_temp': self.forecast_max_temp,
            'forecast_min_temp': self.forecast_min_temp,
            'precipitation_mm': self.precipitation_mm,
            'uv_index': self.uv_index,
            'weather_code': self.weather_code,
            'forecast_condition': self.forecast_condition,
            'pm2_5': self.pm2_5,
            'pm10': self.pm10,
            'us_aqi': self.us_aqi,
            'european_aqi': self.european_aqi,
            'aqi_category': self.aqi_category,
            'data_source': self.data_source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WeatherRecord':
        """Create record from dictionary"""
        # Convert datetime strings to datetime objects
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            try:
                data['last_updated'] = datetime.fromisoformat(data['last_updated'].replace('Z', '+00:00'))
            except:
                data['last_updated'] = datetime.utcnow()
        
        if 'measurement_time' in data and isinstance(data['measurement_time'], str):
            try:
                data['measurement_time'] = datetime.fromisoformat(data['measurement_time'].replace('Z', '+00:00'))
            except:
                data['measurement_time'] = None
        
        return cls(**data)
    
    @classmethod
    def get_latest_for_location(cls, latitude: float, longitude: float, 
                              tolerance: float = 0.01) -> Optional['WeatherRecord']:
        """
        Get the latest weather record for a specific location
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            tolerance: Coordinate tolerance for matching
            
        Returns:
            Latest WeatherRecord or None
        """
        if not db_session:
            logger.error("Database session not initialized")
            return None
        
        try:
            return db_session.query(cls).filter(
                cls.latitude.between(latitude - tolerance, latitude + tolerance),
                cls.longitude.between(longitude - tolerance, longitude + tolerance)
            ).order_by(cls.date.desc(), cls.created_at.desc()).first()
        except Exception as e:
            logger.error(f"Error getting latest record for location: {e}")
            return None
    
    @classmethod
    def get_historical_for_location(cls, latitude: float, longitude: float, 
                                  days: int = 30, tolerance: float = 0.01) -> List['WeatherRecord']:
        """
        Get historical weather records for a location
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days of history to retrieve
            tolerance: Coordinate tolerance for matching
            
        Returns:
            List of WeatherRecord objects
        """
        if not db_session:
            logger.error("Database session not initialized")
            return []
        
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            return db_session.query(cls).filter(
                cls.latitude.between(latitude - tolerance, latitude + tolerance),
                cls.longitude.between(longitude - tolerance, longitude + tolerance),
                cls.date >= cutoff_date
            ).order_by(cls.date.asc()).all()
        except Exception as e:
            logger.error(f"Error getting historical records: {e}")
            return []
    
    @classmethod
    def get_history_for_location(cls, latitude: float, longitude: float, 
                               days: int = 30, tolerance: float = 0.01) -> List['WeatherRecord']:
        """
        Alias for get_historical_for_location to match your app.py expectations
        """
        return cls.get_historical_for_location(latitude, longitude, days, tolerance)
    
    @classmethod
    def get_temperature_series(cls, latitude: float, longitude: float, 
                             days: int = 30, temp_type: str = 'avg') -> pd.Series:
        """
        Get temperature time series for forecasting
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days of history
            temp_type: 'avg', 'max', or 'min'
            
        Returns:
            Pandas Series with date index and temperature values
        """
        records = cls.get_historical_for_location(latitude, longitude, days)
        
        if not records:
            return pd.Series(dtype=float)
        
        # Create DataFrame
        data = []
        for record in records:
            if temp_type == 'max':
                temp = record.forecast_max_temp
            elif temp_type == 'min':
                temp = record.forecast_min_temp
            else:  # avg
                if record.forecast_max_temp and record.forecast_min_temp:
                    temp = (record.forecast_max_temp + record.forecast_min_temp) / 2
                else:
                    temp = record.current_temp_c
            
            if temp is not None:
                data.append({'date': record.date, 'temperature': temp})
        
        if not data:
            return pd.Series(dtype=float)
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        return df['temperature']


class DataQualityLog(Base):
    """
    Log for tracking data quality metrics and ETL performance
    """
    __tablename__ = 'data_quality_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Processing metrics
    records_processed = Column(Integer)
    records_saved = Column(Integer)
    errors_count = Column(Integer, default=0)
    processing_time_seconds = Column(Float)
    
    # Location info
    location_lat = Column(Float)
    location_lon = Column(Float)
    
    # Additional notes
    notes = Column(Text)
    pipeline_version = Column(String(20), default='1.0.0')
    
    def __repr__(self):
        return f"<DataQualityLog(timestamp='{self.timestamp}', records={self.records_saved})>"
    
    @classmethod
    def log_etl_run(cls, records_processed: int, records_saved: int, 
                   processing_time: float, location: Tuple[float, float] = None,
                   errors_count: int = 0, notes: str = ""):
        """
        Log an ETL pipeline run
        
        Args:
            records_processed: Number of records processed
            records_saved: Number of records successfully saved
            processing_time: Processing time in seconds
            location: Tuple of (latitude, longitude)
            errors_count: Number of errors encountered
            notes: Additional notes
        """
        if not db_session:
            logger.error("Database session not initialized")
            return
        
        try:
            log_entry = cls(
                records_processed=records_processed,
                records_saved=records_saved,
                errors_count=errors_count,
                processing_time_seconds=processing_time,
                location_lat=location[0] if location else None,
                location_lon=location[1] if location else None,
                notes=notes
            )
            
            db_session.add(log_entry)
            db_session.commit()
            logger.info(f"Logged ETL run: {records_saved} records saved")
            
        except Exception as e:
            logger.error(f"Error logging ETL run: {e}")
            db_session.rollback()


class LocationSummary(Base):
    """
    Summary statistics for weather data by location
    Updated periodically to provide quick access to location stats
    """
    __tablename__ = 'location_summary'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String(200))  # Optional friendly name
    
    # Data availability
    first_data_date = Column(String(10))
    last_data_date = Column(String(10))
    total_records = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Weather statistics (last 30 days)
    avg_temp = Column(Float)
    min_temp = Column(Float)
    max_temp = Column(Float)
    avg_precipitation = Column(Float)
    avg_aqi = Column(Float)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('latitude', 'longitude', name='_location_uc'),
        Index('idx_location_coords', 'latitude', 'longitude'),
    )
    
    @classmethod
    def update_summary(cls, latitude: float, longitude: float, location_name: str = None):
        """
        Update or create location summary
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            location_name: Optional friendly name for location
        """
        if not db_session:
            logger.error("Database session not initialized")
            return
        
        try:
            # Get existing summary or create new one
            tolerance = 0.01
            summary = db_session.query(cls).filter(
                cls.latitude.between(latitude - tolerance, latitude + tolerance),
                cls.longitude.between(longitude - tolerance, longitude + tolerance)
            ).first()
            
            if not summary:
                summary = cls(latitude=latitude, longitude=longitude)
                db_session.add(summary)
            
            # Update location name if provided
            if location_name:
                summary.location_name = location_name
            
            # Calculate statistics from weather records
            records = WeatherRecord.get_historical_for_location(latitude, longitude, days=30)
            
            if records:
                summary.total_records = len(records)
                summary.first_data_date = min(r.date for r in records)
                summary.last_data_date = max(r.date for r in records)
                
                # Calculate averages
                temps = [r.current_temp_c for r in records if r.current_temp_c is not None]
                max_temps = [r.forecast_max_temp for r in records if r.forecast_max_temp is not None]
                min_temps = [r.forecast_min_temp for r in records if r.forecast_min_temp is not None]
                precip = [r.precipitation_mm for r in records if r.precipitation_mm is not None]
                aqi = [r.us_aqi for r in records if r.us_aqi is not None]
                
                if temps:
                    summary.avg_temp = sum(temps) / len(temps)
                if max_temps:
                    summary.max_temp = max(max_temps)
                if min_temps:
                    summary.min_temp = min(min_temps)
                if precip:
                    summary.avg_precipitation = sum(precip) / len(precip)
                if aqi:
                    summary.avg_aqi = sum(aqi) / len(aqi)
            
            summary.last_updated = datetime.utcnow()
            db_session.commit()
            
            logger.info(f"Updated location summary for {latitude}, {longitude}")
            
        except Exception as e:
            logger.error(f"Error updating location summary: {e}")
            db_session.rollback()


def add_query_property():
    """Add query property to all models after database initialization"""
    if db_session:
        WeatherRecord.query = QueryProperty(db_session)
        DataQualityLog.query = QueryProperty(db_session)
        LocationSummary.query = QueryProperty(db_session)


# Database management functions
def init_database(database_url: str = "sqlite:///data/weather_data.db"):
    """
    Initialize database connection and create tables
    
    Args:
        database_url: Database connection URL
    """
    global db_session, engine
    
    try:
        engine = create_engine(database_url, echo=False)
        Session = sessionmaker(bind=engine)
        db_session = Session()
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Add query property to models
        add_query_property()
        
        logger.info(f"Database initialized successfully: {database_url}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False


def get_session() -> Optional[Session]:
    """Get the current database session"""
    return db_session


def close_database():
    """Close database connection"""
    global db_session, engine
    
    if db_session:
        db_session.close()
        db_session = None
    
    if engine:
        engine.dispose()
        engine = None
    
    logger.info("Database connection closed")


def get_database_stats() -> Dict[str, Any]:
    """
    Get comprehensive database statistics
    
    Returns:
        Dictionary with database statistics
    """
    if not db_session:
        return {"error": "Database not initialized"}
    
    try:
        stats = {}
        
        # Weather records stats
        total_records = db_session.query(WeatherRecord).count()
        stats['total_weather_records'] = total_records
        
        if total_records > 0:
            # Date range
            earliest = db_session.query(func.min(WeatherRecord.date)).scalar()
            latest = db_session.query(func.max(WeatherRecord.date)).scalar()
            stats['date_range'] = {'earliest': earliest, 'latest': latest}
            
            # Unique locations
            unique_locations = db_session.query(
                WeatherRecord.latitude, WeatherRecord.longitude
            ).distinct().count()
            stats['unique_locations'] = unique_locations
            
            # Recent records (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_count = db_session.query(WeatherRecord).filter(
                WeatherRecord.created_at >= yesterday
            ).count()
            stats['records_last_24h'] = recent_count
        
        # Data quality logs
        quality_logs = db_session.query(DataQualityLog).count()
        stats['quality_log_entries'] = quality_logs
        
        # Location summaries
        location_summaries = db_session.query(LocationSummary).count()
        stats['location_summaries'] = location_summaries
        
        stats['last_updated'] = datetime.utcnow().isoformat()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {"error": str(e)}


# Flask-SQLAlchemy compatibility
class FlaskSQLAlchemy:
    """
    Simple Flask-SQLAlchemy compatibility layer
    Allows the models to work with Flask applications
    """
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        database_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///data/weather_data.db')
        init_database(database_url)
        
        # Store session in app context
        app.db_session = db_session
        
        # Cleanup on app teardown
        @app.teardown_appcontext
        def close_db_session(error):
            if db_session:
                db_session.remove()

# Global instance for Flask compatibility
db = FlaskSQLAlchemy()