"""
Helper Utilities for Weather Insight Engine
Common functions used across the Flask application
"""

import requests
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate latitude and longitude coordinates
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
        
    Returns:
        bool: True if coordinates are valid
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
        
        if not (-90 <= lat <= 90):
            return False
        
        if not (-180 <= lon <= 180):
            return False
        
        return True
        
    except (TypeError, ValueError):
        return False


def get_location_name(latitude: float, longitude: float) -> str:
    """
    Get a human-readable location name from coordinates using reverse geocoding
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        str: Location name or formatted coordinates
    """
    try:
        # Try reverse geocoding with OpenStreetMap Nominatim (free service)
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'zoom': 10,
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'WeatherInsightEngine/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract meaningful location name
            address = data.get('address', {})
            
            # Priority order for location components
            location_parts = []
            
            # City/town/village
            city = (address.get('city') or 
                   address.get('town') or 
                   address.get('village') or
                   address.get('municipality'))
            if city:
                location_parts.append(city)
            
            # State/province
            state = (address.get('state') or 
                    address.get('province') or
                    address.get('region'))
            if state and state != city:
                location_parts.append(state)
            
            # Country
            country = address.get('country')
            if country and len(location_parts) < 2:
                location_parts.append(country)
            
            if location_parts:
                return ', '.join(location_parts)
            
            # Fallback to display name
            display_name = data.get('display_name', '')
            if display_name:
                # Take first few components
                parts = display_name.split(',')[:3]
                return ', '.join(part.strip() for part in parts)
        
    except Exception as e:
        logger.warning(f"Failed to get location name for {latitude}, {longitude}: {e}")
    
    # Fallback to formatted coordinates
    return f"{latitude:.2f}°, {longitude:.2f}°"


def categorize_air_quality(aqi: int) -> Dict[str, Any]:
    """
    Categorize AQI value into health categories with colors and descriptions
    
    Args:
        aqi: Air Quality Index value
        
    Returns:
        Dict: AQI category information
    """
    if aqi is None:
        return {
            'category': 'Unknown',
            'color': 'gray',
            'bg_color': 'bg-gray-100',
            'text_color': 'text-gray-800',
            'description': 'Air quality data unavailable',
            'health_advice': 'Monitor air quality from other sources'
        }
    
    try:
        aqi_val = int(aqi)
        
        if aqi_val <= 50:
            return {
                'category': 'Good',
                'color': 'green',
                'bg_color': 'bg-green-100',
                'text_color': 'text-green-800',
                'description': 'Air quality is satisfactory',
                'health_advice': 'Enjoy outdoor activities'
            }
        elif aqi_val <= 100:
            return {
                'category': 'Moderate',
                'color': 'yellow',
                'bg_color': 'bg-yellow-100',
                'text_color': 'text-yellow-800',
                'description': 'Air quality is acceptable',
                'health_advice': 'Sensitive individuals should limit prolonged outdoor exertion'
            }
        elif aqi_val <= 150:
            return {
                'category': 'Unhealthy for Sensitive Groups',
                'color': 'orange',
                'bg_color': 'bg-orange-100',
                'text_color': 'text-orange-800',
                'description': 'Sensitive groups may experience minor issues',
                'health_advice': 'Children, elderly, and people with respiratory conditions should limit outdoor activities'
            }
        elif aqi_val <= 200:
            return {
                'category': 'Unhealthy',
                'color': 'red',
                'bg_color': 'bg-red-100',
                'text_color': 'text-red-800',
                'description': 'Everyone may experience health effects',
                'health_advice': 'Limit outdoor activities, especially prolonged exertion'
            }
        elif aqi_val <= 300:
            return {
                'category': 'Very Unhealthy',
                'color': 'purple',
                'bg_color': 'bg-purple-100',
                'text_color': 'text-purple-800',
                'description': 'Health warnings of emergency conditions',
                'health_advice': 'Avoid outdoor activities'
            }
        else:
            return {
                'category': 'Hazardous',
                'color': 'red',
                'bg_color': 'bg-red-200',
                'text_color': 'text-red-900',
                'description': 'Emergency conditions - health alert',
                'health_advice': 'Stay indoors and avoid all outdoor activities'
            }
            
    except (ValueError, TypeError):
        return {
            'category': 'Invalid',
            'color': 'gray',
            'bg_color': 'bg-gray-100',
            'text_color': 'text-gray-800',
            'description': 'Invalid AQI value',
            'health_advice': 'Check data source'
        }