import pandas as pd
from datetime import datetime


def transform_weather_data(weather_data, air_data):
    """
    Transform Open-Meteo weather and air quality data into a structured format.
    
    Args:
        weather_data (dict): Raw weather data from the forecast API
        air_data (dict): Raw air quality data from the air quality API
        
    Returns:
        list: List of dictionaries with transformed weather data by day
    """
    if not weather_data or not air_data:
        print("[ERROR] No raw data to transform.")
        return []
    
    # Get location data
    latitude = weather_data.get("latitude", "N/A")
    longitude = weather_data.get("longitude", "N/A")
    timezone = weather_data.get("timezone", "N/A")
    
    # Get current weather data
    current = weather_data.get("current_weather", {})
    current_temp = current.get("temperature", "N/A")
    current_windspeed = current.get("windspeed", "N/A")
    current_winddirection = current.get("winddirection", "N/A")
    current_weathercode = current.get("weathercode", 0)
    current_time = current.get("time", datetime.now().strftime("%Y-%m-%dT%H:%M"))
    
    # Get the dates from the forecast
    dates = weather_data.get("daily", {}).get("time", [])
    
    # Get latest air quality data
    latest_air_quality = {}
    if "hourly" in air_data and "time" in air_data["hourly"] and len(air_data["hourly"]["time"]) > 0:
        latest_index = -1  # Get the last (most recent) entry
        latest_air_quality = {
            "pm2_5": air_data["hourly"]["pm2_5"][latest_index] if "pm2_5" in air_data["hourly"] else "N/A",
            "pm10": air_data["hourly"]["pm10"][latest_index] if "pm10" in air_data["hourly"] else "N/A",
            "us_aqi": air_data["hourly"]["us_aqi"][latest_index] if "us_aqi" in air_data["hourly"] else "N/A",
            "time": air_data["hourly"]["time"][latest_index] if "time" in air_data["hourly"] else "N/A"
        }
    
    # Helper function to safely round numbers and handle None/NA values
    def safe_round(value, decimals=2):
        if value is None or value == "N/A":
            return 0
        try:
            return round(float(value), decimals)
        except (TypeError, ValueError):
            return 0
    
    transformed_data = []
    
    # Process each day in the forecast
    for i in range(len(dates)):
        # Create a dictionary for each day
        day_data = {
            "date": dates[i],
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "last_updated": current_time,
            "current_temp_c": current_temp,
            "current_condition": get_weather_description(current_weathercode),
            "wind_kph": current_windspeed,
            "wind_dir": get_wind_direction(current_winddirection),
            "pm2_5": safe_round(latest_air_quality.get("pm2_5")),
            "pm10": safe_round(latest_air_quality.get("pm10")),
            "us_aqi": latest_air_quality.get("us_aqi", "N/A"),
            "aqi_category": get_aqi_category(latest_air_quality.get("us_aqi")),
            "forecast_max_temp": weather_data["daily"]["temperature_2m_max"][i] if "temperature_2m_max" in weather_data["daily"] else "N/A",
            "forecast_min_temp": weather_data["daily"]["temperature_2m_min"][i] if "temperature_2m_min" in weather_data["daily"] else "N/A",
            "precipitation_mm": weather_data["daily"]["precipitation_sum"][i] if "precipitation_sum" in weather_data["daily"] else "N/A",
            "uv_index": weather_data["daily"]["uv_index_max"][i] if "uv_index_max" in weather_data["daily"] else "N/A"
        }
        transformed_data.append(day_data)
    
    print(f"[INFO] Transformed {len(transformed_data)} days of weather data.")
    return transformed_data


def transform_to_dataframe(weather_data, air_data):
    """
    Transform weather data into a pandas DataFrame.
    
    Args:
        weather_data (dict): Raw weather data from the forecast API
        air_data (dict): Raw air quality data from the air quality API
        
    Returns:
        pandas.DataFrame: DataFrame with transformed weather data
    """
    transformed_list = transform_weather_data(weather_data, air_data)
    if not transformed_list:
        return pd.DataFrame()
    
    df = pd.DataFrame(transformed_list)
    return df


def get_weather_description(code):
    """
    Convert Open-Meteo weather codes to human-readable descriptions.
    
    Args:
        code (int): WMO weather code
        
    Returns:
        str: Human-readable weather description
    """
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Light freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Light freezing rain", 67: "Heavy freezing rain",
        71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    
    return weather_codes.get(code, "Unknown")


def get_wind_direction(degrees):
    """
    Convert wind direction in degrees to cardinal direction.
    
    Args:
        degrees (float): Wind direction in degrees
        
    Returns:
        str: Cardinal direction (N, NE, E, etc.)
    """
    if degrees is None or degrees == "N/A":
        return "Unknown"
        
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    index = round(degrees / 22.5) % 16
    return directions[index]


def get_aqi_category(aqi):
    """
    Convert US AQI numerical value to category.
    
    Args:
        aqi (int): US AQI value
        
    Returns:
        str: AQI category description
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