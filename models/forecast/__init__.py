"""
Weather Forecasting Package
Comprehensive ARIMA-based weather forecasting system
"""

# Core forecasting components
try:
    from .core import WeatherForecaster, STATSMODELS_AVAILABLE
    from .manager import ForecastManager
    from .validation import validate_arima_model, validate_forecast_assumptions
    from .metrics import (
        calculate_forecast_accuracy, 
        calculate_directional_accuracy,
        generate_forecast_report
    )
    from .utils import (
        create_synthetic_temperature_series,
        split_time_series,
        detect_outliers,
        smooth_time_series,
        format_forecast_for_display,
        validate_forecast_inputs
    )
    
    # Quick forecast function for convenience
    def quick_forecast(latitude: float, longitude: float, days: int = 3) -> dict:
        """
        Quick temperature forecast for a location
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days to forecast
            
        Returns:
            Dict with forecast results
        """
        manager = ForecastManager()
        return manager.create_temperature_forecast(latitude, longitude, days)
    
    # Package info
    __version__ = "1.0.0"
    __author__ = "Weather Insight Engine"
    
    # Public API
    __all__ = [
        # Core classes
        'WeatherForecaster',
        'ForecastManager',
        
        # Validation functions
        'validate_arima_model',
        'validate_forecast_assumptions',
        
        # Metrics functions
        'calculate_forecast_accuracy',
        'calculate_directional_accuracy',
        'generate_forecast_report',
        
        # Utility functions
        'create_synthetic_temperature_series',
        'split_time_series',
        'detect_outliers',
        'smooth_time_series',
        'format_forecast_for_display',
        'validate_forecast_inputs',
        
        # Quick functions
        'quick_forecast',
        
        # Constants
        'STATSMODELS_AVAILABLE',
    ]

except ImportError as e:
    # Handle case where statsmodels is not installed
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Forecast package import failed: {e}")
    logger.warning("Install statsmodels with: pip install statsmodels")
    
    # Provide stub implementations
    STATSMODELS_AVAILABLE = False
    
    class WeatherForecaster:
        def __init__(self, *args, **kwargs):
            raise ImportError("statsmodels is required for forecasting. Install with: pip install statsmodels")
    
    class ForecastManager:
        def __init__(self, *args, **kwargs):
            raise ImportError("statsmodels is required for forecasting. Install with: pip install statsmodels")
    
    def quick_forecast(*args, **kwargs):
        return {"error": "statsmodels is required for forecasting. Install with: pip install statsmodels"}
    
    # Stub functions
    validate_arima_model = lambda *args, **kwargs: {"error": "statsmodels not available"}
    validate_forecast_assumptions = lambda *args, **kwargs: {"error": "statsmodels not available"}
    calculate_forecast_accuracy = lambda *args, **kwargs: {"error": "statsmodels not available"}
    calculate_directional_accuracy = lambda *args, **kwargs: {"error": "statsmodels not available"}
    generate_forecast_report = lambda *args, **kwargs: {"error": "statsmodels not available"}
    
    # Utility functions that don't require statsmodels
    from .utils import (
        format_forecast_for_display,
        validate_forecast_inputs,
        convert_temperature_units
    )
    
    __all__ = [
        'WeatherForecaster',
        'ForecastManager', 
        'quick_forecast',
        'STATSMODELS_AVAILABLE',
        'format_forecast_for_display',
        'validate_forecast_inputs',
        'convert_temperature_units'
    ]