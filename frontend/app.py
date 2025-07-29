"""
Weather Insight Engine - Flask Web Application
Modern weather dashboard with ARIMA forecasting and beautiful Tailwind CSS interface
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# Local imports
from models.database import init_database, WeatherRecord, get_database_stats
from etl.pipeline import WeatherETLPipeline
from models.forecast import ForecastManager, quick_forecast, STATSMODELS_AVAILABLE
from utils.helpers import validate_coordinates, get_location_name, categorize_air_quality

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
    """Weather display page for a specific location"""
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
        
        # Get the latest weather data from database
        latest_record = WeatherRecord.get_latest_for_location(lat, lon)
        
        # If no recent data, run ETL pipeline
        if not latest_record or _is_data_stale(latest_record):
            logger.info(f"Fetching fresh weather data for {lat}, {lon}")
            pipeline = WeatherETLPipeline()
            success = pipeline.run(lat, lon, display_summary=False)
            
            if success:
                latest_record = WeatherRecord.get_latest_for_location(lat, lon)
            else:
                flash('Unable to fetch weather data. Please try again.', 'error')
                return redirect(url_for('index'))
        
        if not latest_record:
            flash('No weather data available for this location', 'error')
            return redirect(url_for('index'))
        
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
        
        return render_template('weather.html', weather=weather_data)
        
    except Exception as e:
        logger.error(f"Error in weather route: {e}")
        flash('An error occurred while fetching weather data', 'error')
        return redirect(url_for('index'))


@app.route('/history')
def history():
    """Historical weather data page"""
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        days = request.args.get('days', 30, type=int)
        
        if not lat or not lon:
            flash('Please provide valid coordinates', 'error')
            return redirect(url_for('index'))
        
        # Get historical data
        historical_records = WeatherRecord.get_historical_for_location(lat, lon, days=days)
        
        location_name = get_location_name(lat, lon)
        
        # Prepare data for charts
        chart_data = _prepare_chart_data(historical_records)
        
        return render_template('history.html',
                             location={'name': location_name, 'lat': lat, 'lon': lon},
                             historical_data=historical_records,
                             chart_data=chart_data,
                             days=days)
        
    except Exception as e:
        logger.error(f"Error in history route: {e}")
        flash('An error occurred while fetching historical data', 'error')
        return redirect(url_for('index'))


@app.route('/forecast')
def forecast():
    """Detailed forecast page with ARIMA predictions"""
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        if not lat or not lon:
            flash('Please provide valid coordinates', 'error')
            return redirect(url_for('index'))
        
        if not STATSMODELS_AVAILABLE:
            flash('Forecasting not available. Please install statsmodels.', 'error')
            return redirect(url_for('weather', lat=lat, lon=lon))
        
        # Generate forecast
        manager = ForecastManager(min_data_points=5)
        forecast_result = manager.create_temperature_forecast(lat, lon, days=5)
        
        if "error" in forecast_result:
            flash(f'Unable to generate forecast: {forecast_result["error"]}', 'error')
            return redirect(url_for('weather', lat=lat, lon=lon))
        
        location_name = get_location_name(lat, lon)
        
        # Get historical data for context
        historical_records = WeatherRecord.get_historical_for_location(lat, lon, days=30)
        
        return render_template('forecast.html',
                             location={'name': location_name, 'lat': lat, 'lon': lon},
                             forecast=forecast_result,
                             historical_data=historical_records)
        
    except Exception as e:
        logger.error(f"Error in forecast route: {e}")
        flash('An error occurred while generating forecast', 'error')
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


@app.route('/api/forecast/<float:lat>/<float:lon>')
def api_forecast(lat, lon):
    """API endpoint for forecast data"""
    try:
        if not validate_coordinates(lat, lon):
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        if not STATSMODELS_AVAILABLE:
            return jsonify({'error': 'Forecasting not available'}), 503
        
        days = request.args.get('days', 3, type=int)
        forecast_result = quick_forecast(lat, lon, days)
        
        if "error" in forecast_result:
            return jsonify({'error': forecast_result['error']}), 400
        
        return jsonify({
            'success': True,
            'data': forecast_result
        })
        
    except Exception as e:
        logger.error(f"API forecast error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


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


# Helper functions
def _is_data_stale(record, hours=2):
    """Check if weather data is stale (older than specified hours)"""
    if not record.created_at:
        return True
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    return record.created_at < cutoff_time


def _prepare_chart_data(records):
    """Prepare historical data for charts"""
    if not records:
        return {}
    
    dates = [r.date for r in records]
    temps = [r.current_temp_c for r in records if r.current_temp_c is not None]
    max_temps = [r.forecast_max_temp for r in records if r.forecast_max_temp is not None]
    min_temps = [r.forecast_min_temp for r in records if r.forecast_min_temp is not None]
    precipitation = [r.precipitation_mm for r in records if r.precipitation_mm is not None]
    aqi_values = [r.us_aqi for r in records if r.us_aqi is not None]
    
    return {
        'dates': dates,
        'temperature': {
            'current': temps,
            'max': max_temps,
            'min': min_temps
        },
        'precipitation': precipitation,
        'air_quality': aqi_values
    }


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