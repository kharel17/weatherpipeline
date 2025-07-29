"""
Debug ETL Pipeline
Test the weather data fetching to see what's going wrong
Place this file in your project root: /d/Python Project/debug_etl.py
"""

import sys
import os

# This script should be in the project root, so no need to add to path
# But just in case, let's be safe
if not any('Python Project' in path for path in sys.path):
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all modules can be imported"""
    print("🧪 Testing Module Imports...")
    
    try:
        from etl.extract import WeatherExtractor
        print("✅ etl.extract imported")
    except ImportError as e:
        print(f"❌ etl.extract failed: {e}")
        return False
    
    try:
        from etl.transform import WeatherTransformer
        print("✅ etl.transform imported")
    except ImportError as e:
        print(f"❌ etl.transform failed: {e}")
        return False
    
    try:
        from etl.load import WeatherLoader
        print("✅ etl.load imported")
    except ImportError as e:
        print(f"❌ etl.load failed: {e}")
        return False
    
    try:
        from etl.pipeline import WeatherETLPipeline
        print("✅ etl.pipeline imported")
    except ImportError as e:
        print(f"❌ etl.pipeline failed: {e}")
        return False
    
    try:
        from models.database import init_database, WeatherRecord
        print("✅ models.database imported")
    except ImportError as e:
        print(f"❌ models.database failed: {e}")
        return False
    
    try:
        from utils.helpers import validate_coordinates
        print("✅ utils.helpers imported")
    except ImportError as e:
        print(f"❌ utils.helpers failed: {e}")
        return False
    
    return True

def test_api_connectivity():
    """Test API connectivity specifically"""
    print("\n🌐 Testing API Connectivity...")
    
    import requests
    
    # Test Open-Meteo weather API
    try:
        print("Testing Weather API...")
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 27.7,
            "longitude": 85.3,
            "current_weather": "true",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto"
        }
        
        response = requests.get(weather_url, params=params, timeout=10)
        print(f"Weather API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            current_temp = data.get('current_weather', {}).get('temperature')
            print(f"✅ Weather API is working - Current temp: {current_temp}°C")
        else:
            print(f"❌ Weather API error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Weather API connection error: {e}")
        return False
    
    # Test Air Quality API
    try:
        print("Testing Air Quality API...")
        air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": 27.7,
            "longitude": 85.3,
            "hourly": "pm2_5,pm10,us_aqi"
        }
        
        response = requests.get(air_url, params=params, timeout=10)
        print(f"Air Quality API response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Air Quality API is working")
        else:
            print(f"❌ Air Quality API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Air Quality API connection error: {e}")
        return False
    
    return True

def test_data_directory():
    """Test if data directory exists and is writable"""
    print("\n📁 Testing Data Directory...")
    
    try:
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"✅ Created data directory: {data_dir}")
        else:
            print(f"✅ Data directory exists: {data_dir}")
        
        # Test if writable
        test_file = os.path.join(data_dir, "test_write.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("✅ Data directory is writable")
        
        return True
        
    except Exception as e:
        print(f"❌ Data directory error: {e}")
        return False

def test_extractor():
    """Test the weather extractor specifically"""
    print("\n🌍 Testing Weather Extractor...")
    
    try:
        from etl.extract import WeatherExtractor
        
        # Test with Kathmandu coordinates
        lat, lon = 27.7, 85.3
        print(f"Testing location: {lat}, {lon}")
        
        extractor = WeatherExtractor(lat, lon)
        
        # Test weather API
        print("Fetching weather data...")
        weather_data = extractor.fetch_weather_forecast()
        
        if weather_data:
            print("✅ Weather data fetched successfully")
            print(f"   Latitude: {weather_data.get('latitude')}")
            print(f"   Longitude: {weather_data.get('longitude')}")
            print(f"   Timezone: {weather_data.get('timezone')}")
            
            # Check if current weather exists
            current = weather_data.get('current_weather', {})
            if current:
                print(f"   Current temperature: {current.get('temperature')}°C")
            else:
                print("   ⚠️  No current weather data in response")
        else:
            print("❌ Weather data fetch returned None")
            return False
        
        # Test air quality API
        print("Fetching air quality data...")
        air_data = extractor.fetch_air_quality()
        
        if air_data:
            print("✅ Air quality data fetched successfully")
        else:
            print("❌ Air quality data fetch returned None")
            return False
        
        return weather_data, air_data
        
    except Exception as e:
        print(f"❌ Extractor error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transformer(weather_data, air_data):
    """Test the data transformer"""
    print("\n🔄 Testing Data Transformer...")
    
    try:
        from etl.transform import WeatherTransformer
        
        transformer = WeatherTransformer(weather_data, air_data)
        transformed_data = transformer.transform()
        
        if transformed_data:
            print(f"✅ Data transformed successfully: {len(transformed_data)} records")
            
            # Show sample record
            sample = transformed_data[0]
            print(f"   Sample record keys: {list(sample.keys())}")
            print(f"   Date: {sample.get('date')}")
            print(f"   Temperature: {sample.get('current_temp_c')}°C")
            print(f"   Condition: {sample.get('current_condition')}")
            
            return transformed_data
        else:
            print("❌ Data transformation returned empty result")
            return False
            
    except Exception as e:
        print(f"❌ Transformer error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database operations"""
    print("\n💾 Testing Database Operations...")
    
    try:
        from models.database import init_database, WeatherRecord
        
        # Test database initialization
        db_path = "sqlite:///data/weather_test.db"
        success = init_database(db_path)
        
        if success:
            print("✅ Database initialized successfully")
        else:
            print("❌ Database initialization failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_pipeline():
    """Test the complete ETL pipeline"""
    print("\n🚀 Testing Complete ETL Pipeline...")
    
    try:
        from etl.pipeline import WeatherETLPipeline
        
        lat, lon = 27.7, 85.3
        print(f"Running pipeline for {lat}, {lon}")
        
        pipeline = WeatherETLPipeline()
        success = pipeline.run(
            latitude=lat, 
            longitude=lon,
            save_to_db=True,
            save_to_csv=False,
            display_summary=True
        )
        
        if success:
            print("✅ ETL pipeline completed successfully")
            
            # Verify data was saved
            from models.database import WeatherRecord
            latest_record = WeatherRecord.get_latest_for_location(lat, lon)
            
            if latest_record:
                print(f"✅ Data verified in database:")
                print(f"   Date: {latest_record.date}")
                print(f"   Temperature: {latest_record.current_temp_c}°C")
                print(f"   Condition: {latest_record.current_condition}")
                return True
            else:
                print("❌ No data found in database after pipeline run")
                return False
        else:
            print("❌ ETL pipeline failed")
            return False
            
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("🔧 WEATHER INSIGHT ENGINE - ETL DEBUG")
    print("=" * 60)
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")  # Show first 3 paths
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Module import failed. Check your __init__.py files and file structure.")
        return False
    
    # Test 2: Data directory
    if not test_data_directory():
        print("\n❌ Data directory test failed.")
        return False
    
    # Test 3: API connectivity
    if not test_api_connectivity():
        print("\n❌ API connectivity failed. Check your internet connection.")
        return False
    
    # Test 4: Weather extraction
    extraction_result = test_extractor()
    if not extraction_result:
        print("\n❌ Weather extraction failed.")
        return False
    
    weather_data, air_data = extraction_result
    
    # Test 5: Data transformation
    transformed_data = test_transformer(weather_data, air_data)
    if not transformed_data:
        print("\n❌ Data transformation failed.")
        return False
    
    # Test 6: Database
    if not test_database():
        print("\n❌ Database test failed.")
        return False
    
    # Test 7: Full pipeline
    if not test_full_pipeline():
        print("\n❌ Full pipeline test failed.")
        return False
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED!")
    print("Your ETL pipeline is working correctly.")
    print("The weather app should now work properly.")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()