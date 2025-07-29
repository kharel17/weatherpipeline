"""
Enhanced Weather Data Transformer
Improved version with better data validation and error handling
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class WeatherTransformer:
    """
    Enhanced weather data transformer with improved validation and error handling
    """
    
    def __init__(self, weather_data: Dict[str, Any], air_data: Dict[str, Any]):
        """
        Initialize the transformer with raw data
        
        Args:
            weather_data (Dict): Raw weather data from API
            air_data (Dict): Raw air quality data from API
        """
        self.weather_data = weather_data
        self.air_data = air_data
        self.transformed_data = []
        self.errors = []
        
        logger.info("WeatherTransformer initialized")

    def transform(self) -> List[Dict[str, Any]]:
        """
        Transform raw weather and air quality data into standardized format
        
        Returns:
            List[Dict]: List of transformed weather records
        """
        if not self._validate_input_data():
            logger.error("Input data validation failed")
            return []
        
        try:
            logger.info("Starting data transformation")
            
            # Extract basic location and metadata
            location_data = self._extract_location_data()
            current_weather = self._extract_current_weather()
            daily_forecasts = self._extract_daily_forecasts()
            air_quality = self._extract_air_quality()
            
            # Create transformed records for each forecast day
            for i, date in enumerate(daily_forecasts.get('dates', [])):
                try:
                    record = self._create_weather_record(
                        date=date,
                        index=i,
                        location_data=location_data,
                        current_weather=current_weather,
                        daily_forecasts=daily_forecasts,
                        air_quality=air_quality
                    )
                    
                    if self._validate_record(record):
                        self.transformed_data.append(record)
                    else:
                        logger.warning(f"Record validation failed for date {date}")
                        
                except Exception as e:
                    logger.error(f"Error transforming record for date {date}: {e}")
                    self.errors.append(f"Date {date}: {str(e)}")
            
            logger.info(f"Transformation completed. {len(self.transformed_data)} records created")
            
            if self.errors:
                logger.warning(f"Transformation completed with {len(self.errors)} errors")
            
            return self.transformed_data
            
        except Exception as e:
            logger.error(f"Critical error during transformation: {e}")
            return []

    def _validate_input_data(self) -> bool:
        """
        Validate input data structure and content
        
        Returns:
            bool: True if data is valid
        """
        if not self.weather_data or not self.air_data:
            self.errors.append("Missing weather or air quality data")
            return False
        
        # Check weather data structure
        required_weather_keys = ['latitude', 'longitude', 'current_weather', 'daily']
        for key in required_weather_keys:
            if key not in self.weather_data:
                self.errors.append(f"Missing weather data key: {key}")
                return False
        
        # Check air quality data structure
        required_air_keys = ['latitude', 'longitude', 'hourly']
        for key in required_air_keys:
            if key not in self.air_data:
                self.errors.append(f"Missing air quality data key: {key}")
                return False
        
        # Validate coordinates match
        weather_lat = self.weather_data.get('latitude')
        weather_lon = self.weather_data.get('longitude')
        air_lat = self.air_data.get('latitude')
        air_lon = self.air_data.get('longitude')
        
        if abs(weather_lat - air_lat) > 0.1 or abs(weather_lon - air_lon) > 0.1:
            self.errors.append("Weather and air quality coordinates don't match")
            return False
        
        return True

    def _extract_location_data(self) -> Dict[str, Any]:
        """Extract location and metadata"""
        return {
            'latitude': self.weather_data.get('latitude'),
            'longitude': self.weather_data.get('longitude'),
            'timezone': self.weather_data.get('timezone', 'UTC'),
            'elevation': self.weather_data.get('elevation', 0)
        }

    def _extract_current_weather(self) -> Dict[str, Any]:
        """Extract current weather conditions"""
        current = self.weather_data.get('current_weather', {})
        return {
            'temperature': self._safe_float(current.get('temperature')),
            'windspeed': self._safe_float(current.get('windspeed')),
            'winddirection': self._safe_float(current.get('winddirection')),
            'weathercode': self._safe_int(current.get('weathercode')),
            'time': current.get('time', datetime.utcnow().isoformat())
        }

    def _extract_daily_forecasts(self) -> Dict[str, Any]:
        """Extract daily forecast data"""
        daily = self.weather_data.get('daily', {})
        return {
            'dates': daily.get('time', []),
            'max_temps': [self._safe_float(t) for t in daily.get('temperature_2m_max', [])],
            'min_temps': [self._safe_float(t) for t in daily.get('temperature_2m_min', [])],
            'precipitation': [self._safe_float(p) for p in daily.get('precipitation_sum', [])],
            'uv_index': [self._safe_float(uv) for uv in daily.get('uv_index_max', [])],
            'weather_codes': [self._safe_int(wc) for wc in daily.get('weathercode', [])]
        }

    def _extract_air_quality(self) -> Dict[str, Any]:
        """Extract and process air quality data"""
        hourly = self.air_data.get('hourly', {})
        
        # Get the most recent air quality readings
        times = hourly.get('time', [])
        pm2_5_values = [self._safe_float(v) for v in hourly.get('pm2_5', [])]
        pm10_values = [self._safe_float(v) for v in hourly.get('pm10', [])]
        us_aqi_values = [self._safe_int(v) for v in hourly.get('us_aqi', [])]
        eu_aqi_values = [self._safe_int(v) for v in hourly.get('european_aqi', [])]
        
        # Use most recent non-null values
        latest_index = len(times) - 1 if times else 0
        
        return {
            'pm2_5': self._get_latest_valid_value(pm2_5_values, latest_index),
            'pm10': self._get_latest_valid_value(pm10_values, latest_index),
            'us_aqi': self._get_latest_valid_value(us_aqi_values, latest_index),
            'european_aqi': self._get_latest_valid_value(eu_aqi_values, latest_index),
            'measurement_time': times[latest_index] if times else None
        }

    def _create_weather_record(self, date: str, index: int, location_data: Dict, 
                              current_weather: Dict, daily_forecasts: Dict, 
                              air_quality: Dict) -> Dict[str, Any]:
        """
        Create a standardized weather record
        
        Args:
            date (str): Forecast date
            index (int): Index in the daily forecast arrays
            location_data (Dict): Location information
            current_weather (Dict): Current weather data
            daily_forecasts (Dict): Daily forecast data
            air_quality (Dict): Air quality data
            
        Returns:
            Dict: Standardized weather record
        """
        return {
            # Temporal data
            'date': date,
            'last_updated': datetime.utcnow().isoformat(),
            'measurement_time': air_quality.get('measurement_time'),
            
            # Location data
            'latitude': location_data['latitude'],
            'longitude': location_data['longitude'],
            'timezone': location_data['timezone'],
            'elevation': location_data['elevation'],
            
            # Current weather (for reference)
            'current_temp_c': current_weather['temperature'],
            'current_condition': self.get_weather_description(current_weather['weathercode']),
            'wind_kph': current_weather['windspeed'],
            'wind_dir': self.get_wind_direction(current_weather['winddirection']),
            
            # Daily forecast data
            'forecast_max_temp': self._safe_get_list_item(daily_forecasts['max_temps'], index),
            'forecast_min_temp': self._safe_get_list_item(daily_forecasts['min_temps'], index),
            'precipitation_mm': self._safe_get_list_item(daily_forecasts['precipitation'], index),
            'uv_index': self._safe_get_list_item(daily_forecasts['uv_index'], index),
            'weather_code': self._safe_get_list_item(daily_forecasts['weather_codes'], index),
            'forecast_condition': self.get_weather_description(
                self._safe_get_list_item(daily_forecasts['weather_codes'], index)
            ),
            
            # Air quality data
            'pm2_5': air_quality['pm2_5'],
            'pm10': air_quality['pm10'],
            'us_aqi': air_quality['us_aqi'],
            'european_aqi': air_quality['european_aqi'],
            'aqi_category': self.get_aqi_category(air_quality['us_aqi']),
            
            # Metadata
            'data_source': 'open-meteo',
            'created_at': datetime.utcnow().isoformat()
        }

    def _validate_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate a transformed record
        
        Args:
            record (Dict): Weather record to validate
            
        Returns:
            bool: True if record is valid
        """
        # Check required fields
        required_fields = ['date', 'latitude', 'longitude']
        for field in required_fields:
            if field not in record or record[field] is None:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate coordinate ranges
        lat, lon = record['latitude'], record['longitude']
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            logger.warning(f"Invalid coordinates: {lat}, {lon}")
            return False
        
        # Validate temperature ranges (basic sanity check)
        for temp_field in ['current_temp_c', 'forecast_max_temp', 'forecast_min_temp']:
            temp = record.get(temp_field)
            if temp is not None and not (-100 <= temp <= 70):
                logger.warning(f"Temperature out of range: {temp_field}={temp}")
                return False
        
        return True

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        if value is None or value == "N/A":
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Safely convert value to int"""
        if value is None or value == "N/A":
            return default
        try:
            return int(float(value))  # Convert through float to handle "123.0"
        except (TypeError, ValueError):
            return default

    def _safe_get_list_item(self, lst: List, index: int, default: Any = None) -> Any:
        """Safely get item from list by index"""
        try:
            return lst[index] if 0 <= index < len(lst) else default
        except (TypeError, IndexError):
            return default

    def _get_latest_valid_value(self, values: List, start_index: int) -> Any:
        """Get the latest valid (non-None) value from a list"""
        for i in range(start_index, -1, -1):
            if i < len(values) and values[i] is not None:
                return values[i]
        return None

    @staticmethod
    def get_weather_description(code: int) -> str:
        """
        Convert weather code to human-readable description
        
        Args:
            code (int): Weather code from API
            
        Returns:
            str: Weather description
        """
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            56: "Light freezing drizzle", 57: "Dense freezing drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain",
            71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
            77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers", 
            82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        return weather_codes.get(code, f"Unknown ({code})")

    @staticmethod
    def get_wind_direction(degrees: float) -> str:
        """
        Convert wind direction in degrees to compass direction
        
        Args:
            degrees (float): Wind direction in degrees
            
        Returns:
            str: Compass direction
        """
        if degrees is None or degrees == "N/A":
            return "Unknown"
        
        try:
            directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                         "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            index = round(degrees / 22.5) % 16
            return directions[index]
        except (TypeError, ValueError):
            return "Unknown"

    @staticmethod
    def get_aqi_category(aqi: int) -> str:
        """
        Convert AQI value to category description
        
        Args:
            aqi (int): Air Quality Index value
            
        Returns:
            str: AQI category
        """
        if aqi is None or aqi == "N/A":
            return "Unknown"
        
        try:
            aqi = int(aqi)
            if aqi <= 50:
                return "Good"
            elif aqi <= 100:
                return "Moderate"
            elif aqi <= 150:
                return "Unhealthy for Sensitive Groups"
            elif aqi <= 200:
                return "Unhealthy"
            elif aqi <= 300:
                return "Very Unhealthy"
            else:
                return "Hazardous"
        except (ValueError, TypeError):
            return "Unknown"

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert transformed data to pandas DataFrame
        
        Returns:
            pd.DataFrame: DataFrame with transformed data
        """
        if not self.transformed_data:
            logger.warning("No transformed data available for DataFrame conversion")
            return pd.DataFrame()
        
        return pd.DataFrame(self.transformed_data)

    def get_transformation_summary(self) -> Dict[str, Any]:
        """
        Get summary of transformation process
        
        Returns:
            Dict: Transformation summary
        """
        return {
            'total_records': len(self.transformed_data),
            'errors_count': len(self.errors),
            'errors': self.errors,
            'date_range': {
                'start': min(r['date'] for r in self.transformed_data) if self.transformed_data else None,
                'end': max(r['date'] for r in self.transformed_data) if self.transformed_data else None
            },
            'transformation_time': datetime.utcnow().isoformat()
        }