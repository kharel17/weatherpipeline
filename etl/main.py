import argparse
import os
import sys
import time
from datetime import datetime

# Import the ETL modules
import extract
import transform
import load


def run_pipeline(latitude, longitude, save_to_db=True, save_to_csv=True, display_summary=True):
    print("\n===== WEATHER DATA PIPELINE STARTED =====")
    start_time = time.time()
    
    # Step 1: Extract data
    print("\n----- EXTRACTION PHASE -----")
    fetcher = extract.WeatherFetcher(latitude, longitude)
    weather_data = fetcher.fetch_weather_forecast()
    air_data = fetcher.fetch_air_quality()
    
    if not weather_data or not air_data:
        print("[ERROR] Extraction failed. Pipeline terminated.")
        return False
    
    # Step 2: Transform data
    print("\n----- TRANSFORMATION PHASE -----")
    transformer = transform.WeatherTransformer(weather_data, air_data)
    transformed_data = transformer.transform()
    
    if not transformed_data:
        print("[ERROR] Transformation failed. Pipeline terminated.")
        return False
    
    # Step 3: Load data
    print("\n----- LOADING PHASE -----")
    
    # Create loader instance
    loader = load.WeatherLoader(transformed_data)
    
    # Save to SQLite database if requested
    if save_to_db:
        load.WeatherLoader.create_sqlite_tables()  # Ensure tables are created
        db_success = loader.save_to_sqlite()
        if not db_success:
            print("[WARNING] Failed to save data to database.")
    
    # Save to CSV file if requested
    if save_to_csv:
        csv_path = loader.save_to_csv()
        if not csv_path:
            print("[WARNING] Failed to save data to CSV.")
    
    # Display summary if requested
    if display_summary:
        show_data_summary(transformed_data, weather_data, air_data)
    
    # Calculate and display execution time
    execution_time = time.time() - start_time
    print(f"\n===== PIPELINE COMPLETED IN {execution_time:.2f} SECONDS =====")
    
    return True


def show_data_summary(transformed_data, weather_data, air_data):
    # Display data summary
    print("\n----- DATA SUMMARY -----")
    
    # Display basic info
    if transformed_data:
        today = transformed_data[0]  # Get today's forecast
        print(f"\nWeather for: {today['latitude']}, {today['longitude']} ({today['timezone']})")
        print(f"Last updated: {today['last_updated']}")
        
        # Current conditions
        print(f"\nCurrent Conditions:")
        print(f"  Temperature: {today['current_temp_c']}°C")
        print(f"  Condition: {today['current_condition']}")
        print(f"  Wind: {today['wind_kph']} km/h from {today['wind_dir']}")
        
        # Air quality
        print(f"\nAir Quality:")
        print(f"  PM2.5: {today['pm2_5']} µg/m³")
        print(f"  PM10: {today['pm10']} µg/m³")
        print(f"  US AQI: {today['us_aqi']} ({today['aqi_category']})")
        
        # Forecast
        print(f"\n3-Day Forecast:")
        for day in transformed_data[:3]:  # Show first 3 days
            print(f"  {day['date']}: {day['forecast_min_temp']}°C to {day['forecast_max_temp']}°C, " +
                  f"Precipitation: {day['precipitation_mm']} mm, UV Index: {day['uv_index']}")
    else:
        print("No data available to display.")


def parse_arguments():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Weather Data ETL Pipeline')
    
    # Required arguments
    parser.add_argument('--lat', type=float, help='Latitude of the location')
    parser.add_argument('--lon', type=float, help='Longitude of the location')
    
    # Optional arguments
    parser.add_argument('--no-db', action='store_true', help='Skip saving to database')
    parser.add_argument('--no-csv', action='store_true', help='Skip saving to CSV')
    parser.add_argument('--no-summary', action='store_true', help='Skip displaying data summary')
    
    # Predefined locations
    parser.add_argument('--location', type=str, choices=['kathmandu', 'newyork', 'london', 'tokyo', 'sydney'],
                      help='Use a predefined location')
    
    args = parser.parse_args()
    
    # Handle predefined locations
    predefined_locations = {
        'kathmandu': (27.7, 85.3),
        'newyork': (40.71, -74.01),
        'london': (51.51, -0.13),
        'tokyo': (35.69, 139.69),
        'sydney': (-33.87, 151.21)
    }
    
    if args.location:
        args.lat, args.lon = predefined_locations[args.location]
    
    # If no location is provided, default to Kathmandu
    if args.lat is None or args.lon is None:
        args.lat, args.lon = predefined_locations['kathmandu']
        print(f"[INFO] No location specified. Using default: Kathmandu ({args.lat}, {args.lon})")
    
    return args


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Run the pipeline
    success = run_pipeline(
        latitude=args.lat,
        longitude=args.lon,
        save_to_db=not args.no_db,
        save_to_csv=not args.no_csv,
        display_summary=not args.no_summary
    )
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)