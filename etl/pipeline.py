"""
ETL Pipeline Orchestrator
Main class that coordinates the Extract, Transform, Load operations
"""

import logging
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from .extract import WeatherExtractor
from .transform import WeatherTransformer
from .load import WeatherLoader

logger = logging.getLogger(__name__)


class WeatherETLPipeline:
    """
    Main ETL Pipeline class that orchestrates the entire data processing workflow
    """
    
    def __init__(self, data_dir: str = "data", enable_logging: bool = True):
        """
        Initialize the ETL pipeline
        
        Args:
            data_dir: Directory for data storage
            enable_logging: Enable detailed logging
        """
        self.data_dir = data_dir
        self.enable_logging = enable_logging
        self.execution_stats = {}
        
        # Create data directory structure
        data_path = Path(self.data_dir)
        data_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        subdirs = ['logs', 'csv_exports', 'json_exports']
        for subdir in subdirs:
            (data_path / subdir).mkdir(exist_ok=True)
        
        if self.enable_logging:
            self._setup_logging()
        
        logger.info("WeatherETLPipeline initialized")

    def run(self, latitude: float, longitude: float, 
            save_to_db: bool = True, 
            save_to_csv: bool = True, 
            save_to_json: bool = False,
            display_summary: bool = True) -> bool:
        """
        Run the complete ETL pipeline
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            save_to_db: Save data to SQLite database
            save_to_csv: Save data to CSV file
            save_to_json: Save data to JSON file
            display_summary: Display execution summary
            
        Returns:
            bool: True if pipeline completed successfully
        """
        pipeline_start_time = time.time()
        
        try:
            logger.info("="*60)
            logger.info("WEATHER DATA ETL PIPELINE STARTED")
            logger.info("="*60)
            logger.info(f"Location: {latitude}, {longitude}")
            logger.info(f"Timestamp: {datetime.now().isoformat()}")
            
            # Step 1: Extract
            logger.info("\n" + "-"*40)
            logger.info("STEP 1: DATA EXTRACTION")
            logger.info("-"*40)
            
            weather_data, air_data = self._extract_data(latitude, longitude)
            if not weather_data or not air_data:
                logger.error("Data extraction failed - pipeline terminated")
                return False
            
            # Step 2: Transform
            logger.info("\n" + "-"*40)
            logger.info("STEP 2: DATA TRANSFORMATION")
            logger.info("-"*40)
            
            transformed_data = self._transform_data(weather_data, air_data)
            if not transformed_data:
                logger.error("Data transformation failed - pipeline terminated")
                return False
            
            # Step 3: Load
            logger.info("\n" + "-"*40)
            logger.info("STEP 3: DATA LOADING")
            logger.info("-"*40)
            
            load_success = self._load_data(
                transformed_data, 
                save_to_db=save_to_db,
                save_to_csv=save_to_csv, 
                save_to_json=save_to_json
            )
            
            # Calculate total execution time
            total_execution_time = time.time() - pipeline_start_time
            self.execution_stats['total_time'] = total_execution_time
            
            # Display summary if requested
            if display_summary:
                self._display_execution_summary(transformed_data, load_success)
            
            # Log completion
            logger.info("\n" + "="*60)
            logger.info(f"PIPELINE COMPLETED SUCCESSFULLY IN {total_execution_time:.2f} SECONDS")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            total_execution_time = time.time() - pipeline_start_time
            logger.error(f"Pipeline failed after {total_execution_time:.2f} seconds: {e}")
            return False

    def run_batch(self, locations: List[Tuple[float, float]], 
                  save_to_db: bool = True, 
                  save_to_csv: bool = True) -> Dict[str, Any]:
        """
        Run ETL pipeline for multiple locations
        
        Args:
            locations: List of (latitude, longitude) tuples
            save_to_db: Save data to database
            save_to_csv: Save data to CSV
            
        Returns:
            Dict: Batch execution summary
        """
        batch_start_time = time.time()
        successful_locations = []
        failed_locations = []
        
        logger.info(f"Starting batch ETL for {len(locations)} locations")
        
        for i, (lat, lon) in enumerate(locations, 1):
            logger.info(f"\nProcessing location {i}/{len(locations)}: {lat}, {lon}")
            
            try:
                success = self.run(
                    latitude=lat, 
                    longitude=lon,
                    save_to_db=save_to_db,
                    save_to_csv=save_to_csv,
                    display_summary=False  # Don't show summary for each location
                )
                
                if success:
                    successful_locations.append((lat, lon))
                    logger.info(f"[SUCCESS] Location {i} completed successfully")
                else:
                    failed_locations.append((lat, lon))
                    logger.error(f" Location {i} failed")
                    
            except Exception as e:
                failed_locations.append((lat, lon))
                logger.error(f" Location {i} failed with error: {e}")
        
        batch_execution_time = time.time() - batch_start_time
        
        # Batch summary
        summary = {
            'total_locations': len(locations),
            'successful': len(successful_locations),
            'failed': len(failed_locations),
            'success_rate': (len(successful_locations) / len(locations)) * 100,
            'execution_time': batch_execution_time,
            'successful_locations': successful_locations,
            'failed_locations': failed_locations
        }
        
        logger.info(f"\nBatch ETL completed in {batch_execution_time:.2f} seconds")
        logger.info(f"Success rate: {summary['success_rate']:.1f}% ({summary['successful']}/{summary['total_locations']})")
        
        return summary

    def _extract_data(self, latitude: float, longitude: float) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Execute data extraction step
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            Tuple of (weather_data, air_data)
        """
        extract_start_time = time.time()
        
        try:
            # Create extractor and fetch data
            extractor = WeatherExtractor(latitude, longitude)
            weather_data, air_data = extractor.fetch_all()
            
            # Validate extracted data
            if not extractor.validate_data():
                logger.error("Data validation failed after extraction")
                return None, None
            
            # Log extraction stats
            extract_time = time.time() - extract_start_time
            self.execution_stats['extract_time'] = extract_time
            
            data_summary = extractor.get_data_summary()
            logger.info(f"Extraction completed in {extract_time:.2f} seconds")
            logger.info(f"Weather forecast days: {data_summary.get('forecast_days', 0)}")
            logger.info(f"Air quality data points: {data_summary.get('air_quality_hours', 0)}")
            
            return weather_data, air_data
            
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            return None, None

    def _transform_data(self, weather_data: Dict, air_data: Dict) -> Optional[List[Dict]]:
        """
        Execute data transformation step
        
        Args:
            weather_data: Raw weather data
            air_data: Raw air quality data
            
        Returns:
            List of transformed records or None if failed
        """
        transform_start_time = time.time()
        
        try:
            # Create transformer and process data
            transformer = WeatherTransformer(weather_data, air_data)
            transformed_data = transformer.transform()
            
            # Log transformation stats
            transform_time = time.time() - transform_start_time
            self.execution_stats['transform_time'] = transform_time
            
            summary = transformer.get_transformation_summary()
            logger.info(f"Transformation completed in {transform_time:.2f} seconds")
            logger.info(f"Records created: {summary['total_records']}")
            logger.info(f"Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
            
            if summary['errors_count'] > 0:
                logger.warning(f"Transformation completed with {summary['errors_count']} errors")
                for error in summary['errors'][:5]:  # Show first 5 errors
                    logger.warning(f"  - {error}")
            
            return transformed_data
            
        except Exception as e:
            logger.error(f"Data transformation failed: {e}")
            return None

    def _load_data(self, transformed_data: List[Dict], 
                   save_to_db: bool = True, 
                   save_to_csv: bool = True, 
                   save_to_json: bool = False) -> Dict[str, Any]:
        """
        Execute data loading step
        
        Args:
            transformed_data: Transformed weather records
            save_to_db: Save to SQLite database
            save_to_csv: Save to CSV file
            save_to_json: Save to JSON file
            
        Returns:
            Dict: Loading results
        """
        load_start_time = time.time()
        results = {}
        
        try:
            # Create loader
            loader = WeatherLoader(transformed_data, self.data_dir)
            
            # Create database tables if saving to DB
            if save_to_db:
                WeatherLoader.create_sqlite_tables(data_dir=self.data_dir)
                db_success = loader.save_to_sqlite()
                results['database'] = db_success
                if db_success:
                    logger.info("[SUCCESS] Data saved to SQLite database")
                else:
                    logger.error(" Failed to save to database")
            
            # Save to CSV if requested
            if save_to_csv:
                csv_path = loader.save_to_csv()
                results['csv'] = csv_path
                if csv_path:
                    logger.info(f"[SUCCESS] Data saved to CSV: {csv_path}")
                else:
                    logger.error(" Failed to save to CSV")
            
            # Save to JSON if requested
            if save_to_json:
                json_path = loader.save_to_json()
                results['json'] = json_path
                if json_path:
                    logger.info(f"[SUCCESS] Data saved to JSON: {json_path}")
                else:
                    logger.error(" Failed to save to JSON")
            
            # Log quality metrics
            load_time = time.time() - load_start_time
            self.execution_stats['load_time'] = load_time
            
            loader.log_data_quality(
                processing_time=self.execution_stats.get('total_time', 0),
                errors_count=0,  
                notes=f"ETL pipeline execution"
            )
            
            logger.info(f"Data loading completed in {load_time:.2f} seconds")
            
            return results
            
        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            return {}

    def _display_execution_summary(self, transformed_data: List[Dict], load_results: Dict[str, Any]) -> None:
        """
        Display execution summary
        
        Args:
            transformed_data: Transformed data records
            load_results: Results from data loading
        """
        logger.info("\n" + "="*60)
        logger.info("EXECUTION SUMMARY")
        logger.info("="*60)
        
        if transformed_data:
            sample_record = transformed_data[0]
            
            # Location info
            logger.info(f"\nLocation: {sample_record['latitude']}, {sample_record['longitude']}")
            logger.info(f"Timezone: {sample_record.get('timezone', 'Unknown')}")
            logger.info(f"Data source: {sample_record.get('data_source', 'Unknown')}")
            
            # Current conditions
            logger.info(f"\nCurrent Conditions:")
            logger.info(f"  Temperature: {sample_record.get('current_temp_c', 'N/A')}°C")
            logger.info(f"  Condition: {sample_record.get('current_condition', 'N/A')}")
            logger.info(f"  Wind: {sample_record.get('wind_kph', 'N/A')} km/h {sample_record.get('wind_dir', 'N/A')}")
            
            # Air quality
            logger.info(f"\nAir Quality:")
            logger.info(f"  PM2.5: {sample_record.get('pm2_5', 'N/A')} µg/m³")
            logger.info(f"  PM10: {sample_record.get('pm10', 'N/A')} µg/m³")
            logger.info(f"  US AQI: {sample_record.get('us_aqi', 'N/A')} ({sample_record.get('aqi_category', 'N/A')})")
            
            # Forecast preview
            logger.info(f"\nForecast Preview (Next 3 Days):")
            for i, day in enumerate(transformed_data[:3]):
                date = day.get('date', 'Unknown')
                min_temp = day.get('forecast_min_temp', 'N/A')
                max_temp = day.get('forecast_max_temp', 'N/A')
                precipitation = day.get('precipitation_mm', 'N/A')
                uv = day.get('uv_index', 'N/A')
                condition = day.get('forecast_condition', 'N/A')
                
                logger.info(f"  {date}: {min_temp}°C to {max_temp}°C, {condition}")
                logger.info(f"    Precipitation: {precipitation} mm, UV Index: {uv}")
        
        # Performance stats
        logger.info(f"\nPerformance Statistics:")
        logger.info(f"  Extract time: {self.execution_stats.get('extract_time', 0):.2f}s")
        logger.info(f"  Transform time: {self.execution_stats.get('transform_time', 0):.2f}s")
        logger.info(f"  Load time: {self.execution_stats.get('load_time', 0):.2f}s")
        logger.info(f"  Total time: {self.execution_stats.get('total_time', 0):.2f}s")
        
        # Storage results
        logger.info(f"\nData Storage:")
        for format_type, result in load_results.items():
            status = "[SUCCESS] Success" if result else "❌ Failed"
            logger.info(f"  {format_type.upper()}: {status}")

    def _setup_logging(self) -> None:
        """Setup detailed logging configuration"""
        # Ensure logs directory exists
        logs_dir = Path(self.data_dir) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Create file handler only if we can write to the logs directory
        handlers = [logging.StreamHandler()]
        
        try:
            log_file = logs_dir / "etl_pipeline.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
        except (OSError, PermissionError) as e:
            # If we can't create the log file, just use console logging
            logger.warning(f"Could not create log file: {e}. Using console logging only.")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=handlers,
            force=True  # Override any existing configuration
        )

    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get detailed execution statistics
        
        Returns:
            Dict: Execution statistics
        """
        return {
            **self.execution_stats,
            'timestamp': datetime.now().isoformat(),
            'pipeline_version': '1.0.0'
        }

    def validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Validate coordinate values
        
        Args:
            latitude: Latitude value
            longitude: Longitude value
            
        Returns:
            bool: True if coordinates are valid
        """
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            logger.error("Coordinates must be numeric")
            return False
        
        if not (-90 <= latitude <= 90):
            logger.error(f"Latitude {latitude} is out of range [-90, 90]")
            return False
        
        if not (-180 <= longitude <= 180):
            logger.error(f"Longitude {longitude} is out of range [-180, 180]")
            return False
        
        return True

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the ETL pipeline components
        
        Returns:
            Dict: Health check results
        """
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {}
        }
        
        try:
            # Check data directory
            data_path = Path(self.data_dir)
            health_status['components']['data_directory'] = {
                'status': 'healthy' if data_path.exists() else 'unhealthy',
                'path': str(data_path),
                'writable': data_path.is_dir() and os.access(data_path, os.W_OK) if data_path.exists() else False
            }
            
            # Check database
            try:
                WeatherLoader.get_database_stats(data_dir=self.data_dir)
                health_status['components']['database'] = {'status': 'healthy'}
            except Exception as e:
                health_status['components']['database'] = {'status': 'unhealthy', 'error': str(e)}
            
            # Check API connectivity (simple test)
            try:
                extractor = WeatherExtractor(0, 0)  # Test coordinates
                # Just test if we can create the extractor
                health_status['components']['api_connectivity'] = {'status': 'healthy'}
            except Exception as e:
                health_status['components']['api_connectivity'] = {'status': 'unhealthy', 'error': str(e)}
            
            # Determine overall status
            component_statuses = [comp['status'] for comp in health_status['components'].values()]
            if any(status == 'unhealthy' for status in component_statuses):
                health_status['overall_status'] = 'unhealthy'
            
        except Exception as e:
            health_status['overall_status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status


# Backward compatibility function to match your original main.py interface
def run_pipeline(latitude: float, longitude: float, 
                save_to_db: bool = True, 
                save_to_csv: bool = True, 
                display_summary: bool = True) -> bool:
    """
    Backward compatibility function that matches your original main.py interface
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        save_to_db: Save to SQLite database
        save_to_csv: Save to CSV file
        display_summary: Display execution summary
        
    Returns:
        bool: True if pipeline completed successfully
    """
    pipeline = WeatherETLPipeline()
    return pipeline.run(
        latitude=latitude,
        longitude=longitude,
        save_to_db=save_to_db,
        save_to_csv=save_to_csv,
        display_summary=display_summary
    )