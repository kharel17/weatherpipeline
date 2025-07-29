"""
Models module for Weather Insight Engine
Database models and forecasting functionality
"""

from .database import (
    WeatherRecord, 
    DataQualityLog, 
    LocationSummary, 
    init_database, 
    get_session,
    close_database,
    get_database_stats,
    db
)

# Import forecast package
from .forecast import (
    WeatherForecaster, 
    ForecastManager, 
    quick_forecast,
    STATSMODELS_AVAILABLE
)

__all__ = [
    # Database models
    'WeatherRecord', 
    'DataQualityLog', 
    'LocationSummary', 
    'init_database',
    'get_session',
    'close_database',
    'get_database_stats',
    'db',
    
    # Forecasting (from forecast package)
    'WeatherForecaster', 
    'ForecastManager', 
    'quick_forecast',
    'STATSMODELS_AVAILABLE'
]