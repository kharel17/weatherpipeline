"""
Weather Insight Engine - Flask Web Application
Modern weather dashboard with ARIMA forecasting and beautiful Tailwind CSS interface
"""

import os
import sys
import codecs
import sys
import logging
import requests
from datetime import datetime, timedelta, UTC
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for

if sys.platform == "win32":
    if hasattr(sys.stdout, 'detach'):
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    if hasattr(sys.stderr, 'detach'):
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
        
# Add the parent directory to Python path to find our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Local imports - now Python can find them
    from models.database import init_database, WeatherRecord, get_database_stats
    from etl.pipeline import WeatherETLPipeline
    from models.forecast import ForecastManager, quick_forecast, STATSMODELS_AVAILABLE
    from utils.helpers import validate_coordinates, get_location_name, categorize_air_quality
except ImportError as e:
    print(f"Import error: {e}")
    print("Please make sure you're running from the project root directory")
    print("Or install the modules: pip install -e .")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'weather-insight-dev-key-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///data/weather_data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
init_database(app.config['SQLALCHEMY_DATABASE_URI'])

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default locations for quick access
DEFAULT_LOCATIONS = {
    'kathmandu': {'lat': 27.7, 'lon': 85.3, 'name': 'Kathmandu, Nepal'},
    'new_york': {'lat': 40.71, 'lon': -74.01, 'name': 'New York, USA'},
    'london': {'lat': 51.51, 'lon': -0.13, 'name': 'London, UK'},
    'tokyo': {'lat': 35.69, 'lon': 139.69, 'name': 'Tokyo, Japan'},
    'sydney': {'lat': -33.87, 'lon': 151.21, 'name': 'Sydney, Australia'}
}


@app.route('/')
def index():
    """Home page with location search and quick access"""
    return render_template('index.html', 
                         default_locations=DEFAULT_LOCATIONS,
                         favorites=session.get('favorites', []))


@app.route('/weather')
def weather():
    """Weather display page for a specific location - DEBUG VERSION"""
    try:
        # Get coordinates from query parameters
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        logger.info(f"Weather route called with lat={lat}, lon={lon}")
        
        # Enhanced validation
        if lat is None or lon is None:
            flash('Please provide valid coordinates', 'error')
            logger.warning(f"Missing coordinates: lat={lat}, lon={lon}")
            return redirect(url_for('index'))
        
        # Check if coordinates are within valid ranges
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            flash('Coordinates are out of valid range', 'error')
            logger.warning(f"Coordinates out of range: lat={lat}, lon={lon}")
            return redirect(url_for('index'))
        
        # Validate coordinates using existing function
        if not validate_coordinates(lat, lon):
            flash('Invalid coordinates provided', 'error')
            return redirect(url_for('index'))
        
        # Get location name
        location_name = get_location_name(lat, lon)
        logger.info(f"Location name: {location_name}")
        
        # Get the latest weather data from database
        logger.info(f"Attempting to get latest record for {lat}, {lon}")
        latest_record = WeatherRecord.get_latest_for_location(lat, lon)
        logger.info(f"Latest record found: {latest_record is not None}")
        
        # If no recent data, run ETL pipeline
        if not latest_record or _is_data_stale(latest_record):
            logger.info(f"Running ETL pipeline - latest_record: {latest_record is not None}, stale: {_is_data_stale(latest_record) if latest_record else 'N/A'}")
            try:
                pipeline = WeatherETLPipeline()
                success = pipeline.run(lat, lon, display_summary=False)
                logger.info(f"ETL pipeline success: {success}")
                
                if success:
                    # Try to get the record again after ETL
                    logger.info(f"Attempting to get latest record after ETL for {lat}, {lon}")
                    latest_record = WeatherRecord.get_latest_for_location(lat, lon)
                    logger.info(f"Latest record after ETL: {latest_record is not None}")
                    
                    # DEBUG: Let's also try to get records with wider tolerance
                    if not latest_record:
                        logger.warning("No exact match found, trying with wider tolerance...")
                        try:
                            # Try to get any records near this location
                            from models.database import WeatherRecord as WR
                            tolerance = 0.1  # 0.1 degree tolerance
                            nearby_records = WR.query.filter(
                                WR.latitude.between(lat - tolerance, lat + tolerance),
                                WR.longitude.between(lon - tolerance, lon + tolerance)
                            ).order_by(WR.created_at.desc()).limit(5).all()
                            
                            logger.info(f"Found {len(nearby_records)} records within {tolerance} degrees")
                            for i, record in enumerate(nearby_records):
                                logger.info(f"Record {i+1}: lat={record.latitude}, lon={record.longitude}, created={record.created_at}")
                            
                            if nearby_records:
                                latest_record = nearby_records[0]
                                logger.info(f"Using nearby record: lat={latest_record.latitude}, lon={latest_record.longitude}")
                                
                        except Exception as e:
                            logger.error(f"Error checking nearby records: {e}")
                else:
                    flash('Unable to fetch weather data. Please try again later.', 'error')
                    return redirect(url_for('index'))
            except Exception as e:
                logger.error(f"ETL pipeline error: {e}")
                # Check if it's a duplicate record error (not actually an error)
                if not handle_duplicate_record_error(str(e)):
                    flash('Weather service temporarily unavailable. Please try again later.', 'error')
                    return redirect(url_for('index'))
                # If it was just a duplicate, try to get the record again
                latest_record = WeatherRecord.get_latest_for_location(lat, lon)
                logger.info(f"Latest record after handling duplicate error: {latest_record is not None}")
        
        if not latest_record:
            logger.error(f"No weather data available for {lat}, {lon} - this should not happen after successful ETL")
            flash('No weather data available for this location', 'error')
            return redirect(url_for('index'))
        
        logger.info(f"Weather record found: temp={getattr(latest_record, 'temperature', 'N/A')}")
        
        # Get forecast if available
        forecast_data = None
        forecast_error = None
        
        if STATSMODELS_AVAILABLE:
            try:
                manager = ForecastManager(min_data_points=5)
                forecast_result = manager.create_temperature_forecast(lat, lon, days=3)
                
                if "error" not in forecast_result:
                    forecast_data = forecast_result
                else:
                    forecast_error = forecast_result["error"]
            except Exception as e:
                forecast_error = str(e)
        else:
            forecast_error = "Forecasting not available (statsmodels not installed)"
        
        # Prepare weather data for template
        weather_data = {
            'current': latest_record.to_dict(),
            'location': {
                'name': location_name,
                'lat': lat,
                'lon': lon
            },
            'air_quality': categorize_air_quality(latest_record.us_aqi),
            'forecast': forecast_data,
            'forecast_error': forecast_error
        }
        
        logger.info(f"Rendering weather template for {location_name}")
        return render_template('weather.html', weather=weather_data)
        
    except Exception as e:
        logger.error(f"Error in weather route: {e}", exc_info=True)
        flash('An error occurred while fetching weather data', 'error')
        return redirect(url_for('index'))


@app.route('/history')
def history():
    """Historical weather data page"""
    try:
        # Get coordinates from query parameters
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        if not lat or not lon:
            flash('Please provide valid coordinates', 'error')
            return redirect(url_for('index'))
        
        # Validate coordinates
        if not validate_coordinates(lat, lon):
            flash('Invalid coordinates provided', 'error')
            return redirect(url_for('index'))
        
        # Get location name
        location_name = get_location_name(lat, lon)
        
        # Get historical records using your existing class methods
        historical_records = []
        try:
            # Use your existing class method
            historical_records = WeatherRecord.get_historical_for_location(lat, lon, days=30)
            
            # If no records found, try with wider tolerance
            if not historical_records:
                historical_records = WeatherRecord.get_historical_for_location(lat, lon, days=60, tolerance=0.1)
                
        except Exception as e:
            logger.error(f"Error getting historical records: {e}")
            flash('Error accessing historical data', 'error')
            return redirect(url_for('index'))
        
        # Prepare historical data
        history_data = {
            'location': {
                'name': location_name,
                'lat': lat,
                'lon': lon
            },
            'records': []
        }
        
        # Convert records to dictionaries
        if historical_records:
            try:
                history_data['records'] = [record.to_dict() for record in historical_records]
            except Exception as e:
                logger.error(f"Error converting records to dict: {e}")
                flash('Error processing historical data', 'error')
                return redirect(url_for('index'))
        
        if not history_data['records']:
            flash('No historical data available for this location. Try fetching current weather first.', 'info')
        
        return render_template('history.html', history=history_data)
        
    except Exception as e:
        logger.error(f"Error in history route: {e}")
        flash('An error occurred while fetching historical data', 'error')
        return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    """Multi-location dashboard"""
    favorites = session.get('favorites', [])
    
    if not favorites:
        flash('Add some favorite locations to see your dashboard', 'info')
        return redirect(url_for('index'))
    
    dashboard_data = []
    
    for fav in favorites:
        try:
            lat, lon = fav['lat'], fav['lon']
            latest_record = WeatherRecord.get_latest_for_location(lat, lon)
            
            if latest_record:
                weather_summary = {
                    'location': fav,
                    'weather': latest_record.to_dict(),
                    'air_quality': categorize_air_quality(latest_record.us_aqi)
                }
                dashboard_data.append(weather_summary)
        except Exception as e:
            logger.error(f"Error getting data for {fav}: {e}")
    
    return render_template('dashboard.html', dashboard_data=dashboard_data)


@app.route('/forecast')
def forecast():
    """ARIMA forecast page for a specific location"""
    try:
        # Get coordinates from query parameters
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        if not lat or not lon:
            flash('Please provide valid coordinates', 'error')
            return redirect(url_for('index'))
        
        # Validate coordinates
        if not validate_coordinates(lat, lon):
            flash('Invalid coordinates provided', 'error')
            return redirect(url_for('index'))
        
        # Get location name
        location_name = get_location_name(lat, lon)
        
        # Get detailed forecast if ARIMA is available
        forecast_data = None
        forecast_error = None
        
        if STATSMODELS_AVAILABLE:
            try:
                manager = ForecastManager(min_data_points=5)
                forecast_result = manager.create_temperature_forecast(lat, lon, days=7)
                
                if "error" not in forecast_result:
                    forecast_data = forecast_result
                else:
                    forecast_error = forecast_result["error"]
            except Exception as e:
                forecast_error = str(e)
        else:
            forecast_error = "Forecasting not available (statsmodels not installed)"
        
        # Prepare forecast data for template
        forecast_info = {
            'location': {
                'name': location_name,
                'lat': lat,
                'lon': lon
            },
            'forecast': forecast_data,
            'forecast_error': forecast_error
        }
        
        return render_template('forecast.html', forecast=forecast_info)
        
    except Exception as e:
        logger.error(f"Error in forecast route: {e}")
        flash('An error occurred while generating forecast', 'error')
        return redirect(url_for('index'))


@app.route('/stats')
def stats():
    """System statistics page"""
    try:
        db_stats = get_database_stats()
        
        system_stats = {
            'database': db_stats,
            'forecasting_available': STATSMODELS_AVAILABLE,
            'total_favorites': len(session.get('favorites', [])),
            'app_version': '1.0.0'
        }
        
        return render_template('stats.html', stats=system_stats)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        flash('Error loading statistics', 'error')
        return redirect(url_for('index'))


# API Routes
@app.route('/api/weather/<float:lat>/<float:lon>')
def api_weather(lat, lon):
    """API endpoint for weather data"""
    try:
        if not validate_coordinates(lat, lon):
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        latest_record = WeatherRecord.get_latest_for_location(lat, lon)
        
        if not latest_record:
            return jsonify({'error': 'No weather data available'}), 404
        
        return jsonify({
            'success': True,
            'data': latest_record.to_dict(),
            'location_name': get_location_name(lat, lon)
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/history/<float:lat>/<float:lon>')
def api_history(lat, lon):
    """API endpoint for historical weather data"""
    try:
        if not validate_coordinates(lat, lon):
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)  # Limit to 1 year
        
        try:
            records = WeatherRecord.get_history_for_location(lat, lon, days=days)
        except AttributeError:
            # Fallback if method doesn't exist
            from sqlalchemy import desc
            records = WeatherRecord.query.filter(
                WeatherRecord.latitude.between(lat - 0.01, lat + 0.01),
                WeatherRecord.longitude.between(lon - 0.01, lon + 0.01)
            ).order_by(desc(WeatherRecord.created_at)).limit(days * 4).all()  # 4 records per day max
        
        if not records:
            return jsonify({'error': 'No historical data available'}), 404
        
        return jsonify({
            'success': True,
            'data': [record.to_dict() for record in records],
            'location_name': get_location_name(lat, lon)
        })
        
    except Exception as e:
        logger.error(f"API history error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/geocode/<city_name>')
def api_geocode(city_name):
    """API endpoint to convert city name to coordinates"""
    try:
        # Use OpenStreetMap Nominatim for geocoding
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': city_name,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'WeatherInsightEngine/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data:
                location = data[0]
                return jsonify({
                    'success': True,
                    'latitude': float(location['lat']),
                    'longitude': float(location['lon']),
                    'display_name': location['display_name'],
                    'name': location.get('name', city_name)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Location not found'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Geocoding service unavailable'
            }), 503
            
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/update-weather', methods=['POST'])
def api_update_weather():
    """API endpoint to trigger weather data update"""
    try:
        data = request.get_json()
        lat = data.get('lat')
        lon = data.get('lon')
        
        if not lat or not lon or not validate_coordinates(lat, lon):
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        # Run ETL pipeline
        pipeline = WeatherETLPipeline()
        success = pipeline.run(lat, lon, display_summary=False)
        
        if success:
            return jsonify({'success': True, 'message': 'Weather data updated'})
        else:
            return jsonify({'error': 'Failed to update weather data'}), 500
            
    except Exception as e:
        logger.error(f"API update error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Session management routes
@app.route('/add-favorite', methods=['POST'])
def add_favorite():
    """Add location to favorites"""
    try:
        data = request.get_json()
        lat = data.get('lat')
        lon = data.get('lon')
        name = data.get('name', get_location_name(lat, lon))
        
        if not validate_coordinates(lat, lon):
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        if 'favorites' not in session:
            session['favorites'] = []
        
        # Check if already in favorites
        for fav in session['favorites']:
            if abs(fav['lat'] - lat) < 0.01 and abs(fav['lon'] - lon) < 0.01:
                return jsonify({'error': 'Location already in favorites'}), 400
        
        # Add to favorites
        session['favorites'].append({
            'lat': lat,
            'lon': lon,
            'name': name,
            'added_at': datetime.now().isoformat()
        })
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Added to favorites'})
        
    except Exception as e:
        logger.error(f"Add favorite error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/remove-favorite', methods=['POST'])
def remove_favorite():
    """Remove location from favorites"""
    try:
        data = request.get_json()
        lat = data.get('lat')
        lon = data.get('lon')
        
        if 'favorites' not in session:
            return jsonify({'error': 'No favorites found'}), 400
        
        # Remove from favorites
        session['favorites'] = [
            fav for fav in session['favorites']
            if not (abs(fav['lat'] - lat) < 0.01 and abs(fav['lon'] - lon) < 0.01)
        ]
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Removed from favorites'})
        
    except Exception as e:
        logger.error(f"Remove favorite error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Helper functions
def _is_data_stale(record, hours=2):
    """Check if weather data is stale (older than specified hours)"""
    if not record.created_at:
        return True
    
    # Fixed deprecation warning by using datetime.now(UTC)
    cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
    # Handle both timezone-aware and naive datetime objects
    if record.created_at.tzinfo is None:
        cutoff_time = cutoff_time.replace(tzinfo=None)
    
    return record.created_at < cutoff_time


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500


# Template context processors
@app.context_processor
def inject_globals():
    """Inject global variables into templates"""
    return {
        'app_name': 'Weather Insight Engine',
        'current_year': datetime.now().year,
        'forecasting_available': STATSMODELS_AVAILABLE
    }


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Weather Insight Engine on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Forecasting available: {STATSMODELS_AVAILABLE}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)