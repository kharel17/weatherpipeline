"""
Enhanced Weather Data Extractor
Improved version with error handling, retries, and logging
"""

import requests
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class WeatherExtractor:
    """
    Enhanced weather data extractor with retry logic and error handling
    """
    
    def __init__(self, latitude: float, longitude: float, timeout: int = 30, max_retries: int = 3):
        """
        Initialize the weather extractor
        
        Args:
            latitude (float): Location latitude
            longitude (float): Location longitude
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retry attempts
        """
        self.latitude = latitude
        self.longitude = longitude
        self.timeout = timeout
        self.max_retries = max_retries
        self.weather_data = None
        self.air_data = None
        
        # API endpoints
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
        self.air_quality_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        
        logger.info(f"WeatherExtractor initialized for coordinates: {latitude}, {longitude}")

    def _make_request_with_retry(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with retry logic
        
        Args:
            url (str): API endpoint URL
            params (Dict): Request parameters
            
        Returns:
            Optional[Dict]: JSON response or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making request to {url}, attempt {attempt + 1}")
                
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()  # Raises HTTPError for bad responses
                
                data = response.json()
                logger.debug(f"Request successful on attempt {attempt + 1}")
                return data
                
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
                if e.response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                elif e.response.status_code >= 500:  # Server error
                    wait_time = 2 ** attempt
                    logger.info(f"Server error. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Client error {e.response.status_code}: {e}")
                    break
                    
            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                time.sleep(1)
                
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                break
                
        logger.error(f"All {self.max_retries} attempts failed for {url}")
        return None

    def fetch_weather_forecast(self) -> Optional[Dict[str, Any]]:
        """
        Fetch weather forecast data from Open-Meteo API
        
        Returns:
            Optional[Dict]: Weather data or None if failed
        """
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,uv_index_max,weathercode",
            "current_weather": "true",
            "timezone": "auto",
            "past_days": 7  # Get 7 days of forecast
        }
        
        logger.info(f"Fetching weather forecast for {self.latitude}, {self.longitude}")
        
        self.weather_data = self._make_request_with_retry(self.weather_url, params)
        
        if self.weather_data:
            logger.info("Weather forecast fetched successfully")
            # Add metadata
            self.weather_data['fetch_timestamp'] = datetime.utcnow().isoformat()
            self.weather_data['source'] = 'open-meteo'
        else:
            logger.error("Failed to fetch weather forecast")
            
        return self.weather_data

    def fetch_air_quality(self) -> Optional[Dict[str, Any]]:
        """
        Fetch air quality data from Open-Meteo Air Quality API
        
        Returns:
            Optional[Dict]: Air quality data or None if failed
        """
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": "pm2_5,pm10,us_aqi,european_aqi",
            "timezone": "auto"
        }
        
        logger.info(f"Fetching air quality data for {self.latitude}, {self.longitude}")
        
        self.air_data = self._make_request_with_retry(self.air_quality_url, params)
        
        if self.air_data:
            logger.info("Air quality data fetched successfully")
            # Add metadata
            self.air_data['fetch_timestamp'] = datetime.utcnow().isoformat()
            self.air_data['source'] = 'open-meteo-air-quality'
        else:
            logger.error("Failed to fetch air quality data")
            
        return self.air_data

    def fetch_all(self) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Fetch both weather and air quality data
        
        Returns:
            tuple: (weather_data, air_data)
        """
        logger.info("Starting complete data extraction")
        start_time = time.time()
        
        weather = self.fetch_weather_forecast()
        air = self.fetch_air_quality()
        
        execution_time = time.time() - start_time
        logger.info(f"Data extraction completed in {execution_time:.2f} seconds")
        
        return weather, air

    def validate_data(self) -> bool:
        """
        Validate fetched data for completeness and correctness
        
        Returns:
            bool: True if data is valid, False otherwise
        """
        if not self.weather_data or not self.air_data:
            logger.error("Missing weather or air quality data")
            return False
        
        # Validate weather data structure
        required_weather_keys = ['latitude', 'longitude', 'current_weather', 'daily']
        for key in required_weather_keys:
            if key not in self.weather_data:
                logger.error(f"Missing required weather data key: {key}")
                return False
        
        # Validate current weather data
        current = self.weather_data.get('current_weather', {})
        if 'temperature' not in current or 'time' not in current:
            logger.error("Invalid current weather data structure")
            return False
        
        # Validate daily forecast data
        daily = self.weather_data.get('daily', {})
        required_daily_keys = ['time', 'temperature_2m_max', 'temperature_2m_min']
        for key in required_daily_keys:
            if key not in daily:
                logger.error(f"Missing required daily weather key: {key}")
                return False
        
        # Validate air quality data structure
        required_air_keys = ['latitude', 'longitude', 'hourly']
        for key in required_air_keys:
            if key not in self.air_data:
                logger.error(f"Missing required air quality data key: {key}")
                return False
        
        # Validate hourly air quality data
        hourly = self.air_data.get('hourly', {})
        if 'time' not in hourly or not any(key in hourly for key in ['pm2_5', 'pm10', 'us_aqi']):
            logger.error("Invalid air quality data structure")
            return False
        
        logger.info("Data validation successful")
        return True

    def get_data_summary(self) -> Dict[str, Any]:
        """
        Get summary of fetched data
        
        Returns:
            Dict: Summary information
        """
        if not self.weather_data or not self.air_data:
            return {"status": "no_data", "message": "No data available"}
        
        current = self.weather_data.get('current_weather', {})
        daily = self.weather_data.get('daily', {})
        hourly_air = self.air_data.get('hourly', {})
        
        return {
            "status": "success",
            "location": {
                "latitude": self.weather_data.get('latitude'),
                "longitude": self.weather_data.get('longitude'),
                "timezone": self.weather_data.get('timezone')
            },
            "current_temperature": current.get('temperature'),
            "current_time": current.get('time'),
            "forecast_days": len(daily.get('time', [])),
            "air_quality_hours": len(hourly_air.get('time', [])),
            "fetch_time": self.weather_data.get('fetch_timestamp')
        }


# Legacy compatibility - keeping your original class name for backward compatibility
class WeatherFetcher(WeatherExtractor):
    """
    Backward compatibility alias for WeatherExtractor
    Maintains the same interface as your original code
    """
    pass