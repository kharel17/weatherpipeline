# test_etl.py - Quick test of enhanced ETL modules
from etl.extract import WeatherExtractor
from etl.transform import WeatherTransformer

# Test with Kathmandu coordinates
lat, lon = 27.7, 85.3

print("Testing Enhanced ETL Pipeline...")
print(f"Location: {lat}, {lon}")

# Test extraction
extractor = WeatherExtractor(lat, lon)
weather_data, air_data = extractor.fetch_all()

if weather_data and air_data:
    print("✅ Data extraction successful")
    
    # Test transformation
    transformer = WeatherTransformer(weather_data, air_data)
    transformed_data = transformer.transform()
    
    if transformed_data:
        print(f"✅ Data transformation successful: {len(transformed_data)} records")
        print("Sample record:", transformed_data[0])
    else:
        print("❌ Transformation failed")
else:
    print("❌ Extraction failed")