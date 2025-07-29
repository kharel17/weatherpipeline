"""
Forecast Utilities
Helper functions for weather forecasting operations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

def create_synthetic_temperature_series(days: int = 30, base_temp: float = 20.0, 
                                      trend: float = 0.1, seasonality: float = 5.0,
                                      noise_std: float = 2.0) -> pd.Series:
    """
    Create synthetic temperature data for testing
    
    Args:
        days: Number of days to generate
        base_temp: Base temperature
        trend: Daily trend (warming/cooling)
        seasonality: Amplitude of seasonal variation
        noise_std: Standard deviation of random noise
        
    Returns:
        pd.Series: Synthetic temperature time series
    """
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')
    
    # Create temperature components
    trend_component = trend * np.arange(days)
    seasonal_component = seasonality * np.sin(2 * np.pi * np.arange(days) / 365.25)
    weekly_component = 2 * np.sin(2 * np.pi * np.arange(days) / 7)
    noise_component = np.random.normal(0, noise_std, days)
    
    temperatures = base_temp + trend_component + seasonal_component + weekly_component + noise_component
    
    return pd.Series(temperatures, index=dates)


def split_time_series(data: pd.Series, train_ratio: float = 0.8) -> Tuple[pd.Series, pd.Series]:
    """
    Split time series data into training and testing sets
    
    Args:
        data: Time series data
        train_ratio: Proportion of data for training
        
    Returns:
        Tuple of (training_data, testing_data)
    """
    split_point = int(len(data) * train_ratio)
    train_data = data.iloc[:split_point]
    test_data = data.iloc[split_point:]
    
    return train_data, test_data


def detect_outliers(data: pd.Series, method: str = 'iqr', factor: float = 1.5) -> List[int]:
    """
    Detect outliers in time series data
    
    Args:
        data: Time series data
        method: Outlier detection method ('iqr', 'zscore')
        factor: Threshold factor for outlier detection
        
    Returns:
        List of outlier indices
    """
    outlier_indices = []
    
    if method == 'iqr':
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR
        
        outlier_indices = data[(data < lower_bound) | (data > upper_bound)].index.tolist()
        
    elif method == 'zscore':
        z_scores = np.abs((data - data.mean()) / data.std())
        outlier_indices = data[z_scores > factor].index.tolist()
    
    return outlier_indices


def smooth_time_series(data: pd.Series, method: str = 'rolling', window: int = 3) -> pd.Series:
    """
    Smooth time series data to reduce noise
    
    Args:
        data: Time series data
        method: Smoothing method ('rolling', 'ewm')
        window: Window size for smoothing
        
    Returns:
        Smoothed time series
    """
    if method == 'rolling':
        return data.rolling(window=window, center=True).mean().fillna(data)
    elif method == 'ewm':
        return data.ewm(span=window).mean()
    else:
        return data


def calculate_seasonal_decomposition(data: pd.Series, period: int = 365) -> Dict[str, pd.Series]:
    """
    Decompose time series into trend, seasonal, and residual components
    
    Args:
        data: Time series data
        period: Period for seasonal decomposition
        
    Returns:
        Dict with trend, seasonal, and residual components
    """
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # Ensure we have enough data for decomposition
        if len(data) < 2 * period:
            period = max(7, len(data) // 3)  # Use weekly or smaller period
        
        decomposition = seasonal_decompose(data, model='additive', period=period)
        
        return {
            'trend': decomposition.trend,
            'seasonal': decomposition.seasonal,
            'residual': decomposition.resid,
            'observed': decomposition.observed
        }
        
    except ImportError:
        # Fallback to simple moving average for trend
        trend = data.rolling(window=period, center=True).mean()
        seasonal = data - trend
        residual = data - trend - seasonal.rolling(window=period, center=True).mean()
        
        return {
            'trend': trend,
            'seasonal': seasonal,
            'residual': residual,
            'observed': data
        }


def format_forecast_for_display(forecast_data: List[Dict[str, Any]]) -> str:
    """
    Format forecast data for human-readable display
    
    Args:
        forecast_data: List of forecast dictionaries
        
    Returns:
        Formatted string representation
    """
    if not forecast_data:
        return "No forecast data available"
    
    lines = ["Weather Forecast:"]
    lines.append("-" * 40)
    
    for item in forecast_data:
        date = item.get('date', 'Unknown')
        temp = item.get('forecast_temp', 'N/A')
        lower = item.get('lower_bound', 'N/A')
        upper = item.get('upper_bound', 'N/A')
        
        lines.append(f"{date}: {temp}°C ({lower}°C - {upper}°C)")
    
    return '\n'.join(lines)


def validate_forecast_inputs(latitude: float, longitude: float, days: int, 
                           historical_days: int) -> Dict[str, Any]:
    """
    Validate inputs for forecast generation
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of forecast days
        historical_days: Number of historical days
        
    Returns:
        Dict with validation results
    """
    errors = []
    warnings = []
    
    # Validate coordinates
    if not (-90 <= latitude <= 90):
        errors.append(f"Invalid latitude: {latitude} (must be between -90 and 90)")
    
    if not (-180 <= longitude <= 180):
        errors.append(f"Invalid longitude: {longitude} (must be between -180 and 180)")
    
    # Validate forecast parameters
    if days < 1:
        errors.append(f"Invalid forecast days: {days} (must be >= 1)")
    elif days > 30:
        warnings.append(f"Long forecast horizon: {days} days (accuracy may be low)")
    
    if historical_days < 10:
        errors.append(f"Insufficient historical days: {historical_days} (minimum 10 required)")
    elif historical_days < 30:
        warnings.append(f"Limited historical data: {historical_days} days (30+ recommended)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def convert_temperature_units(temp_celsius: float, target_unit: str = 'fahrenheit') -> float:
    """
    Convert temperature between units
    
    Args:
        temp_celsius: Temperature in Celsius
        target_unit: Target unit ('fahrenheit', 'kelvin')
        
    Returns:
        Converted temperature
    """
    if target_unit.lower() in ['fahrenheit', 'f']:
        return (temp_celsius * 9/5) + 32
    elif target_unit.lower() in ['kelvin', 'k']:
        return temp_celsius + 273.15
    else:
        return temp_celsius  # Return as-is for Celsius


def get_forecast_confidence_description(confidence_level: float) -> str:
    """
    Get human-readable description of confidence level
    
    Args:
        confidence_level: Confidence level (0.0 to 1.0)
        
    Returns:
        Description string
    """
    if confidence_level >= 0.95:
        return "Very High Confidence"
    elif confidence_level >= 0.90:
        return "High Confidence"
    elif confidence_level >= 0.80:
        return "Moderate Confidence"
    elif confidence_level >= 0.70:
        return "Low Confidence"
    else:
        return "Very Low Confidence"


def calculate_forecast_uncertainty(forecast_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate uncertainty metrics for forecast
    
    Args:
        forecast_data: List of forecast dictionaries with bounds
        
    Returns:
        Dict with uncertainty metrics
    """
    if not forecast_data:
        return {"error": "No forecast data provided"}
    
    uncertainties = []
    for item in forecast_data:
        lower = item.get('lower_bound')
        upper = item.get('upper_bound')
        
        if lower is not None and upper is not None:
            uncertainty = upper - lower
            uncertainties.append(uncertainty)
    
    if uncertainties:
        return {
            "mean_uncertainty": np.mean(uncertainties),
            "max_uncertainty": np.max(uncertainties),
            "min_uncertainty": np.min(uncertainties),
            "uncertainty_trend": "increasing" if len(uncertainties) > 1 and uncertainties[-1] > uncertainties[0] else "stable"
        }
    else:
        return {"error": "No valid uncertainty bounds found"}