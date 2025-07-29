"""
Forecast Manager
High-level interface for weather forecasting operations
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Tuple

from .core import WeatherForecaster
from .validation import validate_arima_model, validate_forecast_assumptions
from .metrics import generate_forecast_report

logger = logging.getLogger(__name__)


class ForecastManager:
    """
    High-level manager for weather forecasting operations
    Integrates with database models and provides easy-to-use interface
    """
    
    def __init__(self, min_data_points: int = 10):
        """
        Initialize forecast manager
        
        Args:
            min_data_points: Minimum data points required for forecasting
        """
        self.min_data_points = min_data_points
        self.forecasters = {}  # Cache forecasters by location
        
        logger.info("ForecastManager initialized")
    
    def create_temperature_forecast(self, latitude: float, longitude: float, 
                                  days: int = 3, historical_days: int = 30,
                                  temp_type: str = 'avg') -> Dict[str, Any]:
        """
        Create temperature forecast for a specific location
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days to forecast
            historical_days: Days of historical data to use
            temp_type: Type of temperature ('avg', 'max', 'min')
            
        Returns:
            Dict with forecast results
        """
        try:
            # Import here to avoid circular imports
            from ..database import WeatherRecord
            
            logger.info(f"Creating {days}-day {temp_type} temperature forecast for {latitude}, {longitude}")
            
            # Get temperature time series from database
            temp_series = WeatherRecord.get_temperature_series(
                latitude, longitude, historical_days, temp_type
            )
            
            if temp_series.empty:
                return {
                    "error": "No historical temperature data available",
                    "location": {"latitude": latitude, "longitude": longitude},
                    "required_data_points": self.min_data_points
                }
            
            if len(temp_series) < self.min_data_points:
                return {
                    "error": f"Insufficient data: {len(temp_series)} points (minimum {self.min_data_points} required)",
                    "location": {"latitude": latitude, "longitude": longitude},
                    "available_data_points": len(temp_series),
                    "required_data_points": self.min_data_points
                }
            
            # Validate forecast assumptions
            assumptions = validate_forecast_assumptions(temp_series)
            if not assumptions.get("overall_valid", False):
                return {
                    "error": "Data does not meet forecasting assumptions",
                    "validation_details": assumptions
                }
            
            # Create forecaster
            forecaster = WeatherForecaster()
            
            # Prepare data
            if not forecaster.prepare_data(temp_series, self.min_data_points):
                return {"error": "Failed to prepare data for forecasting"}
            
            # Check stationarity
            stationarity = forecaster.check_stationarity()
            
            # Fit model
            if not forecaster.fit_model(auto_select=True):
                return {"error": "Failed to fit forecasting model"}
            
            # Validate model
            validation = validate_arima_model(forecaster.fitted_model)
            
            # Generate forecast
            forecast_result = forecaster.generate_forecast(steps=days)
            
            if "error" in forecast_result:
                return forecast_result
            
            # Add additional metadata
            forecast_result["location"] = {
                "latitude": latitude,
                "longitude": longitude
            }
            forecast_result["temperature_type"] = temp_type
            forecast_result["stationarity_test"] = stationarity
            forecast_result["model_validation"] = validation
            forecast_result["data_assumptions"] = assumptions
            
            # Cache forecaster for potential reuse
            location_key = f"{latitude:.2f},{longitude:.2f}"
            self.forecasters[location_key] = forecaster
            
            logger.info(f"Forecast created successfully for {latitude}, {longitude}")
            
            return forecast_result
            
        except Exception as e:
            logger.error(f"Error creating temperature forecast: {e}")
            return {"error": str(e)}
    
    def create_multi_location_forecast(self, locations: List[Tuple[float, float]], 
                                     days: int = 3) -> Dict[str, Any]:
        """
        Create forecasts for multiple locations
        
        Args:
            locations: List of (latitude, longitude) tuples
            days: Number of days to forecast
            
        Returns:
            Dict with forecasts for all locations
        """
        results = {
            "forecasts": {},
            "summary": {
                "total_locations": len(locations),
                "successful": 0,
                "failed": 0,
                "errors": []
            }
        }
        
        for lat, lon in locations:
            try:
                location_key = f"{lat:.2f},{lon:.2f}"
                forecast = self.create_temperature_forecast(lat, lon, days)
                
                results["forecasts"][location_key] = forecast
                
                if "error" in forecast:
                    results["summary"]["failed"] += 1
                    results["summary"]["errors"].append({
                        "location": location_key,
                        "error": forecast["error"]
                    })
                else:
                    results["summary"]["successful"] += 1
                    
            except Exception as e:
                results["summary"]["failed"] += 1
                results["summary"]["errors"].append({
                    "location": f"{lat:.2f},{lon:.2f}",
                    "error": str(e)
                })
        
        success_rate = (results["summary"]["successful"] / len(locations)) * 100
        results["summary"]["success_rate"] = success_rate
        
        logger.info(f"Multi-location forecast: {success_rate:.1f}% success rate")
        
        return results
    
    def get_forecast_performance(self, latitude: float, longitude: float,
                               days_back: int = 7) -> Dict[str, Any]:
        """
        Analyze forecast performance by comparing past forecasts with actual data
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            days_back: How many days back to analyze
            
        Returns:
            Dict with performance analysis
        """
        try:
            from ..database import WeatherRecord
            
            # Get recent historical data
            historical_data = WeatherRecord.get_historical_for_location(
                latitude, longitude, days=days_back + 30
            )
            
            if len(historical_data) < days_back + self.min_data_points:
                return {"error": "Insufficient data for performance analysis"}
            
            # Split data: use older data for training, recent data for comparison
            split_point = len(historical_data) - days_back
            training_data = historical_data[:split_point]
            actual_data = historical_data[split_point:]
            
            # Create time series from training data
            training_series = pd.Series(
                [r.current_temp_c for r in training_data if r.current_temp_c is not None],
                index=pd.to_datetime([r.date for r in training_data if r.current_temp_c is not None])
            )
            
            if len(training_series) < self.min_data_points:
                return {"error": "Insufficient training data"}
            
            # Create forecaster and generate forecast
            forecaster = WeatherForecaster()
            if not forecaster.prepare_data(training_series):
                return {"error": "Failed to prepare training data"}
            
            if not forecaster.fit_model():
                return {"error": "Failed to fit model for performance analysis"}
            
            forecast_result = forecaster.generate_forecast(steps=len(actual_data))
            
            if "error" in forecast_result:
                return forecast_result
            
            # Compare with actual data
            actual_temps = [r.current_temp_c for r in actual_data if r.current_temp_c is not None]
            actual_series = pd.Series(actual_temps)
            
            # Generate comprehensive report
            performance_report = generate_forecast_report(forecast_result, actual_series)
            
            return {
                "performance_report": performance_report,
                "forecast_period": {
                    "start": actual_data[0].date,
                    "end": actual_data[-1].date,
                    "days": len(actual_data)
                },
                "model_info": forecaster.get_model_summary()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing forecast performance: {e}")
            return {"error": str(e)}
    
    def get_cached_forecaster(self, latitude: float, longitude: float) -> WeatherForecaster:
        """
        Get cached forecaster for a location or None if not available
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            WeatherForecaster instance or None
        """
        location_key = f"{latitude:.2f},{longitude:.2f}"
        return self.forecasters.get(location_key)
    
    def clear_forecaster_cache(self, latitude: float = None, longitude: float = None):
        """
        Clear forecaster cache for specific location or all locations
        
        Args:
            latitude: Optional location latitude
            longitude: Optional location longitude
        """
        if latitude is not None and longitude is not None:
            location_key = f"{latitude:.2f},{longitude:.2f}"
            self.forecasters.pop(location_key, None)
            logger.info(f"Cleared forecaster cache for {location_key}")
        else:
            self.forecasters.clear()
            logger.info("Cleared all forecaster cache")
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the forecast manager
        
        Returns:
            Dict with manager statistics
        """
        return {
            "cached_forecasters": len(self.forecasters),
            "cached_locations": list(self.forecasters.keys()),
            "min_data_points": self.min_data_points
        }