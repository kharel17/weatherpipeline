import requests

def fetch_weather_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,uv_index_max",
        "current_weather": "true",
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        print("[INFO] Weather forecast fetched successfully.")
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch weather forecast: {e}")
        return None

def fetch_air_quality(lat, lon):
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5,pm10,us_aqi",
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        print("[INFO] Air quality data fetched successfully.")
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch air quality data: {e}")
        return None

def display_summary(weather_data, air_data):
    if not weather_data or not air_data:
        print("[ERROR] Missing data. Cannot display summary.")
        return

    # Current weather
    current = weather_data.get("current_weather", {})
    print(f"\n Location (Lat/Lon): {weather_data['latitude']}, {weather_data['longitude']}")
    print(f" Time: {current.get('time')}")
    print(f" Current Temp: {current.get('temperature')}°C, Windspeed: {current.get('windspeed')} km/h")

    # 3-Day forecast
    print("\n 3-Day Forecast:")
    for i in range(3):
        date = weather_data["daily"]["time"][i]
        tmax = weather_data["daily"]["temperature_2m_max"][i]
        tmin = weather_data["daily"]["temperature_2m_min"][i]
        uv = weather_data["daily"]["uv_index_max"][i]
        precip = weather_data["daily"]["precipitation_sum"][i]
        print(f"  - {date}: Max {tmax}°C, Min {tmin}°C, UV Index: {uv}, Rain: {precip}mm")

    # Air quality
    print("\n Air Quality Summary (Last Recorded Hour):")
    try:
        pm2_5 = air_data["hourly"]["pm2_5"][-1]
        pm10 = air_data["hourly"]["pm10"][-1]
        aqi = air_data["hourly"]["us_aqi"][-1]
        time = air_data["hourly"]["time"][-1]
        print(f"  - Time: {time}")
        print(f"  - PM2.5: {pm2_5} µg/m³")
        print(f"  - PM10: {pm10} µg/m³")
        print(f"  - US AQI: {aqi}")
    except IndexError:
        print("[ERROR] No recent air quality data found.")

# ----- EXECUTION -----
if __name__ == "__main__":
    LAT = 27.7      # Kathmandu Latitude
    LON = 85.3      # Kathmandu Longitude

    weather = fetch_weather_forecast(LAT, LON)
    air = fetch_air_quality(LAT, LON)
    display_summary(weather, air)
