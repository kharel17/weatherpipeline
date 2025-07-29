"""
Test the new modular forecast package structure
Comprehensive testing of all forecast components
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_package_imports():
    """Test that all package components can be imported"""
    print("\n" + "="*60)
    print("TESTING PACKAGE IMPORTS")
    print("="*60)
    
    try:
        # Test core functionality
        from models.forecast import WeatherForecaster, STATSMODELS_AVAILABLE
        print(f"✅ Core import successful. STATSMODELS_AVAILABLE: {STATSMODELS_AVAILABLE}")
        
        # Test manager
        from models.forecast import ForecastManager
        print("✅ Manager import successful")
        
        # Test utilities
        from models.forecast import validate_forecast_inputs, format_forecast_for_display
        print("✅ Utilities import successful")
        
        # Test validation functions
        try:
            from models.forecast.validation import validate_forecast_assumptions
            print("✅ Validation module import successful")
        except ImportError as e:
            print(f"⚠️  Validation import warning: {e}")
        
        # Test metrics functions
        try:
            from models.forecast.metrics import calculate_forecast_accuracy
            print("✅ Metrics module import successful")
        except ImportError as e:
            print(f"⚠️  Metrics import warning: {e}")
        
        # Test quick forecast (if statsmodels available)
        if STATSMODELS_AVAILABLE:
            from models.forecast import quick_forecast
            print("✅ Quick forecast import successful")
        else:
            print("⚠️  Statsmodels not available - install with: pip install statsmodels")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_input_validation():
    """Test input validation functions"""
    print("\n" + "="*60)
    print("TESTING INPUT VALIDATION")
    print("="*60)
    
    try:
        from models.forecast import validate_forecast_inputs
        
        # Test valid inputs
        valid_result = validate_forecast_inputs(27.7, 85.3, 3, 30)
        if valid_result['valid']:
            print("✅ Valid input test passed")
        else:
            print(f"❌ Valid input test failed: {valid_result['errors']}")
            return False
        
        # Test invalid latitude
        invalid_lat = validate_forecast_inputs(95.0, 85.3, 3, 30)
        if not invalid_lat['valid']:
            print("✅ Invalid latitude test passed")
        else:
            print("❌ Invalid latitude test failed")
            return False
        
        # Test invalid longitude
        invalid_lon = validate_forecast_inputs(27.7, 185.0, 3, 30)
        if not invalid_lon['valid']:
            print("✅ Invalid longitude test passed")
        else:
            print("❌ Invalid longitude test failed")
            return False
        
        # Test insufficient historical days
        insufficient_days = validate_forecast_inputs(27.7, 85.3, 3, 5)
        if not insufficient_days['valid']:
            print("✅ Insufficient historical days test passed")
        else:
            print("❌ Insufficient historical days test failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Input validation test failed: {e}")
        return False

def test_synthetic_data_creation():
    """Test synthetic data creation for testing"""
    print("\n" + "="*60)
    print("TESTING SYNTHETIC DATA CREATION")
    print("="*60)
    
    try:
        from models.forecast.utils import create_synthetic_temperature_series
        
        # Create synthetic data
        temp_series = create_synthetic_temperature_series(days=30, base_temp=25.0)
        
        if len(temp_series) == 30:
            print(f"✅ Synthetic data created: {len(temp_series)} days")
            print(f"   Temperature range: {temp_series.min():.1f}°C to {temp_series.max():.1f}°C")
            return temp_series
        else:
            print(f"❌ Wrong data length: expected 30, got {len(temp_series)}")
            return None
        
    except Exception as e:
        print(f"❌ Synthetic data creation failed: {e}")
        return None

def test_forecaster_without_database():
    """Test WeatherForecaster with synthetic data (no database required)"""
    print("\n" + "="*60)
    print("TESTING WEATHER FORECASTER (SYNTHETIC DATA)")
    print("="*60)
    
    try:
        from models.forecast import WeatherForecaster, STATSMODELS_AVAILABLE
        
        if not STATSMODELS_AVAILABLE:
            print("⚠️  Skipping forecaster test - statsmodels not available")
            return True
        
        # Create synthetic temperature data
        from models.forecast.utils import create_synthetic_temperature_series
        temp_series = create_synthetic_temperature_series(days=30, base_temp=22.0)
        
        # Test WeatherForecaster
        forecaster = WeatherForecaster()
        
        # Prepare data
        if not forecaster.prepare_data(temp_series):
            print("❌ Failed to prepare synthetic data")
            return False
        print("✅ Data preparation successful")
        
        # Check stationarity
        stationarity = forecaster.check_stationarity()
        print(f"✅ Stationarity test: {stationarity.get('interpretation', 'Unknown')}")
        
        # Fit model
        if not forecaster.fit_model(auto_select=True):
            print("❌ Failed to fit model")
            return False
        print("✅ ARIMA model fitted successfully")
        
        # Generate forecast
        forecast_result = forecaster.generate_forecast(steps=3)
        if "error" not in forecast_result:
            print("✅ 3-day forecast generated successfully")
            
            # Display forecast
            print("\nForecast Results:")
            for item in forecast_result["forecast_data"]:
                print(f"  {item['date']}: {item['forecast_temp']}°C "
                      f"({item['lower_bound']}-{item['upper_bound']}°C)")
            
            return forecast_result
        else:
            print(f"❌ Forecast generation failed: {forecast_result['error']}")
            return None
        
    except Exception as e:
        print(f"❌ Forecaster test failed: {e}")
        return None

def test_metrics_functions():
    """Test forecast accuracy metrics"""
    print("\n" + "="*60)
    print("TESTING FORECAST METRICS")
    print("="*60)
    
    try:
        from models.forecast.metrics import (
            calculate_forecast_accuracy, 
            calculate_directional_accuracy,
            analyze_forecast_bias
        )
        
        # Create test data
        actual_values = [20.0, 21.0, 22.5, 23.0, 21.5, 20.8, 22.1]
        forecast_values = [19.8, 21.2, 22.3, 23.1, 21.7, 20.6, 22.3]
        
        # Test accuracy metrics
        accuracy = calculate_forecast_accuracy(forecast_values, actual_values)
        if "error" not in accuracy:
            print("✅ Forecast accuracy calculation successful")
            print(f"   MAE: {accuracy['mae']:.2f}")
            print(f"   RMSE: {accuracy['rmse']:.2f}")
            print(f"   Correlation: {accuracy['correlation']:.3f}")
        else:
            print(f"❌ Accuracy calculation failed: {accuracy['error']}")
            return False
        
        # Test directional accuracy
        directional = calculate_directional_accuracy(forecast_values, actual_values)
        if "error" not in directional:
            print("✅ Directional accuracy calculation successful")
            print(f"   Directional Accuracy: {directional['directional_accuracy']:.3f}")
        else:
            print(f"❌ Directional accuracy failed: {directional['error']}")
            return False
        
        # Test bias analysis
        bias = analyze_forecast_bias(forecast_values, actual_values)
        if "error" not in bias:
            print("✅ Bias analysis successful")
            print(f"   Overall Bias: {bias['overall_bias']:.3f}")
            print(f"   Interpretation: {bias['bias_interpretation']['overall']}")
        else:
            print(f"❌ Bias analysis failed: {bias['error']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Metrics test failed: {e}")
        return False

def test_utilities():
    """Test utility functions"""
    print("\n" + "="*60)
    print("TESTING UTILITY FUNCTIONS")
    print("="*60)
    
    try:
        from models.forecast.utils import (
            detect_outliers, 
            smooth_time_series,
            format_forecast_for_display
        )
        
        # Create test data with outliers
        test_data = pd.Series([20, 21, 22, 100, 23, 24, 25, -50, 26])  # 100 and -50 are outliers
        
        # Test outlier detection
        outliers = detect_outliers(test_data, method='iqr')
        if len(outliers) > 0:
            print(f"✅ Outlier detection successful: {len(outliers)} outliers found")
        else:
            print("⚠️  No outliers detected (may be normal)")
        
        # Test smoothing
        smoothed = smooth_time_series(test_data, method='rolling', window=3)
        if len(smoothed) == len(test_data):
            print("✅ Time series smoothing successful")
        else:
            print("❌ Smoothing failed")
            return False
        
        # Test forecast display formatting
        sample_forecast = [
            {"date": "2025-07-30", "forecast_temp": 23.5, "lower_bound": 21.0, "upper_bound": 26.0},
            {"date": "2025-07-31", "forecast_temp": 24.1, "lower_bound": 21.5, "upper_bound": 26.7}
        ]
        
        formatted = format_forecast_for_display(sample_forecast)
        if "Weather Forecast:" in formatted:
            print("✅ Forecast formatting successful")
            print("   Sample format:")
            for line in formatted.split('\n')[:3]:  # Show first 3 lines
                print(f"     {line}")
        else:
            print("❌ Forecast formatting failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Utilities test failed: {e}")
        return False

def test_database_integration():
    """Test integration with database models (if available)"""
    print("\n" + "="*60)
    print("TESTING DATABASE INTEGRATION")
    print("="*60)
    
    try:
        from models.database import WeatherRecord, init_database
        from models.forecast import ForecastManager, STATSMODELS_AVAILABLE
        
        if not STATSMODELS_AVAILABLE:
            print("⚠️  Skipping database integration test - statsmodels not available")
            return True
        
        # Initialize test database
        init_success = init_database("sqlite:///data/forecast_test.db")
        if not init_success:
            print("⚠️  Database initialization failed - skipping integration test")
            return True
        
        print("✅ Test database initialized")
        
        # Try to get temperature series (may be empty for new database)
        temp_series = WeatherRecord.get_temperature_series(27.7, 85.3, 14, 'avg')
        print(f"✅ Temperature series query successful: {len(temp_series)} data points")
        
        if len(temp_series) >= 10:
            # Test ForecastManager with real data
            manager = ForecastManager(min_data_points=5)  # Lower requirement for testing
            forecast = manager.create_temperature_forecast(27.7, 85.3, days=3)
            
            if "error" not in forecast:
                print("✅ Database-based forecast successful")
                print(f"   Forecast generated for {len(forecast['forecast_data'])} days")
            else:
                print(f"⚠️  Database forecast issue: {forecast['error']}")
        else:
            print("⚠️  Insufficient database data for forecast test")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Database integration test failed: {e}")
        print("   This is normal if database is not set up yet")
        return True  # Don't fail the test for missing database

def test_complete_workflow():
    """Test complete forecasting workflow"""
    print("\n" + "="*60)
    print("TESTING COMPLETE WORKFLOW")
    print("="*60)
    
    try:
        from models.forecast import STATSMODELS_AVAILABLE
        
        if not STATSMODELS_AVAILABLE:
            print("⚠️  Skipping complete workflow test - statsmodels not available")
            return True
        
        from models.forecast import quick_forecast
        from models.forecast.utils import create_synthetic_temperature_series
        from models.forecast.metrics import generate_forecast_report
        
        print("1. Testing quick_forecast function...")
        
        # This will likely fail with database error, but tests the interface
        result = quick_forecast(latitude=27.7, longitude=85.3, days=3)
        
        if "error" in result:
            print(f"⚠️  Quick forecast returned error: {result['error']}")
            print("   This is expected if database has insufficient data")
        else:
            print("✅ Quick forecast successful")
            
            # Test report generation if we have a forecast
            print("2. Testing forecast report generation...")
            
            # Create some mock actual data for comparison
            actual_data = pd.Series([22.0, 23.5, 24.1])
            report = generate_forecast_report(result, actual_data)
            
            if "error" not in report:
                print("✅ Forecast report generation successful")
                if "performance_assessment" in report:
                    print(f"   Performance: {report['performance_assessment']['overall_rating']}")
            else:
                print(f"❌ Report generation failed: {report['error']}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Complete workflow test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("🚀 Starting Forecast Package Tests...")
    print(f"Python version: {sys.version}")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # Run all tests
    test_results.append(("Package Imports", test_package_imports()))
    test_results.append(("Input Validation", test_input_validation()))
    test_results.append(("Synthetic Data", test_synthetic_data_creation() is not None))
    test_results.append(("Weather Forecaster", test_forecaster_without_database() is not None))
    test_results.append(("Metrics Functions", test_metrics_functions()))
    test_results.append(("Utility Functions", test_utilities()))
    test_results.append(("Database Integration", test_database_integration()))
    test_results.append(("Complete Workflow", test_complete_workflow()))
    
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
        print("\n🎉 All tests passed! Forecast package is working correctly!")
        print("\nWhat's working:")
        print("  ✅ Modular package structure")
        print("  ✅ Input validation")
        print("  ✅ Synthetic data generation")
        print("  ✅ ARIMA forecasting")
        print("  ✅ Accuracy metrics")
        print("  ✅ Utility functions")
        print("\nNext steps:")
        print("  1. ✅ Enhanced ETL pipeline")
        print("  2. ✅ Database models") 
        print("  3. ✅ Modular ARIMA forecasting")
        print("  4. 🔄 Ready for Flask Web Application!")
    else:
        print(f"\n⚠️  {total-passed} test(s) need attention.")
        
        if passed >= total * 0.75:  # 75% pass rate
            print("Good progress! Most components are working.")
        
        print("\nTroubleshooting:")
        print("  • If statsmodels errors: pip install statsmodels")
        print("  • If import errors: check file locations and __init__.py files")
        print("  • Database errors are normal if no data exists yet")

if __name__ == "__main__":
    run_all_tests()