"""
Test the Enhanced ETL Pipeline
This script tests all the enhanced ETL components working together
"""

import logging
from etl.pipeline import WeatherETLPipeline, run_pipeline
from etl.load import WeatherLoader

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_single_location():
    """Test ETL pipeline for a single location"""
    print("\n" + "="*60)
    print("TESTING ENHANCED ETL PIPELINE - SINGLE LOCATION")
    print("="*60)
    
    # Test coordinates (Kathmandu)
    lat, lon = 27.7, 85.3
    
    # Create and run pipeline
    pipeline = WeatherETLPipeline(data_dir="data")
    
    success = pipeline.run(
        latitude=lat,
        longitude=lon,
        save_to_db=True,
        save_to_csv=True,
        save_to_json=True,  # Also test JSON export
        display_summary=True
    )
    
    if success:
        print("\n✅ Single location test PASSED")
        
        # Show execution stats
        stats = pipeline.get_execution_stats()
        print(f"\nExecution Statistics:")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    else:
        print("\n❌ Single location test FAILED")
    
    return success

def test_multiple_locations():
    """Test ETL pipeline for multiple locations"""
    print("\n" + "="*60)
    print("TESTING ENHANCED ETL PIPELINE - MULTIPLE LOCATIONS")
    print("="*60)
    
    # Test locations
    locations = [
        (27.7, 85.3),    # Kathmandu
        (40.71, -74.01), # New York
        (51.51, -0.13),  # London
    ]
    
    pipeline = WeatherETLPipeline(data_dir="data")
    
    batch_results = pipeline.run_batch(
        locations=locations,
        save_to_db=True,
        save_to_csv=True
    )
    
    print(f"\nBatch Results:")
    print(f"  Total locations: {batch_results['total_locations']}")
    print(f"  Successful: {batch_results['successful']}")
    print(f"  Failed: {batch_results['failed']}")
    print(f"  Success rate: {batch_results['success_rate']:.1f}%")
    print(f"  Total time: {batch_results['execution_time']:.2f} seconds")
    
    success = batch_results['success_rate'] >= 80  # At least 80% success rate
    
    if success:
        print("\n✅ Multiple locations test PASSED")
    else:
        print("\n❌ Multiple locations test FAILED")
    
    return success

def test_database_operations():
    """Test database operations and querying"""
    print("\n" + "="*60)
    print("TESTING DATABASE OPERATIONS")
    print("="*60)
    
    try:
        # Get database stats
        stats = WeatherLoader.get_database_stats(data_dir="data")
        print(f"Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Query latest data
        latest_data = WeatherLoader.query_latest_data(data_dir="data", limit=5)
        print(f"\nLatest Data Query:")
        print(f"  Records retrieved: {len(latest_data)}")
        
        if not latest_data.empty:
            print(f"  Columns: {list(latest_data.columns)}")
            print(f"  Date range: {latest_data['date'].min()} to {latest_data['date'].max()}")
        
        print("\n✅ Database operations test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Database operations test FAILED: {e}")
        return False

def test_backward_compatibility():
    """Test backward compatibility with original interface"""
    print("\n" + "="*60)
    print("TESTING BACKWARD COMPATIBILITY")
    print("="*60)
    
    try:
        # Test using the old interface (like your original main.py)
        success = run_pipeline(
            latitude=27.7,
            longitude=85.3,
            save_to_db=True,
            save_to_csv=True,
            display_summary=False  # Keep it quiet for this test
        )
        
        if success:
            print("✅ Backward compatibility test PASSED")
            print("   Your existing code will work with the enhanced pipeline!")
        else:
            print("❌ Backward compatibility test FAILED")
        
        return success
        
    except Exception as e:
        print(f"❌ Backward compatibility test FAILED: {e}")
        return False

def test_health_check():
    """Test pipeline health check functionality"""
    print("\n" + "="*60)
    print("TESTING HEALTH CHECK")
    print("="*60)
    
    try:
        pipeline = WeatherETLPipeline(data_dir="data")
        health = pipeline.health_check()
        
        print(f"Health Check Results:")
        print(f"  Overall Status: {health['overall_status']}")
        print(f"  Components:")
        
        for component, status in health['components'].items():
            status_emoji = "✅" if status['status'] == 'healthy' else "❌"
            print(f"    {component}: {status_emoji} {status['status']}")
            if 'error' in status:
                print(f"      Error: {status['error']}")
        
        success = health['overall_status'] == 'healthy'
        
        if success:
            print("\n✅ Health check test PASSED")
        else:
            print("\n❌ Health check test FAILED")
        
        return success
        
    except Exception as e:
        print(f"❌ Health check test FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Enhanced ETL Pipeline Tests...")
    
    test_results = []
    
    # Run all tests
    test_results.append(("Single Location", test_single_location()))
    test_results.append(("Multiple Locations", test_multiple_locations()))
    test_results.append(("Database Operations", test_database_operations()))
    test_results.append(("Backward Compatibility", test_backward_compatibility()))
    test_results.append(("Health Check", test_health_check()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Your enhanced ETL pipeline is ready!")
        print("\nNext steps:")
        print("  1. ✅ Enhanced ETL pipeline is working")
        print("  2. 🔄 Ready for Step 3: Database Models & ARIMA Forecasting")
    else:
        print(f"\n⚠️  {total-passed} test(s) failed. Please check the errors above.")

if __name__ == "__main__":
    main()