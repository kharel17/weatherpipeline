"""
Forecast Accuracy Metrics
Functions for calculating forecast performance and accuracy
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def calculate_forecast_accuracy(forecast_values: List[float], actual_values: List[float]) -> Dict[str, float]:
    """
    Calculate comprehensive forecast accuracy metrics
    
    Args:
        forecast_values: Predicted values
        actual_values: Actual observed values
        
    Returns:
        Dict with accuracy metrics
    """
    try:
        # Ensure same length
        min_length = min(len(forecast_values), len(actual_values))
        forecast_array = np.array(forecast_values[:min_length])
        actual_array = np.array(actual_values[:min_length])
        
        # Calculate errors
        errors = actual_array - forecast_array
        abs_errors = np.abs(errors)
        squared_errors = errors**2
        
        # Basic metrics
        mae = np.mean(abs_errors)  # Mean Absolute Error
        mse = np.mean(squared_errors)  # Mean Squared Error
        rmse = np.sqrt(mse)  # Root Mean Squared Error
        
        # Percentage errors (avoid division by zero)
        non_zero_actual = actual_array[actual_array != 0]
        non_zero_forecast = forecast_array[actual_array != 0]
        
        if len(non_zero_actual) > 0:
            percentage_errors = np.abs((non_zero_actual - non_zero_forecast) / non_zero_actual) * 100
            mape = np.mean(percentage_errors)  # Mean Absolute Percentage Error
        else:
            mape = float('inf')
        
        # Symmetric MAPE (handles zeros better)
        smape = np.mean(2 * abs_errors / (np.abs(actual_array) + np.abs(forecast_array))) * 100
        
        # Mean Bias Error
        mbe = np.mean(errors)
        
        # Correlation coefficient
        correlation = np.corrcoef(forecast_array, actual_array)[0, 1] if len(forecast_array) > 1 else 0
        
        # Theil's U statistic
        if len(actual_array) > 1:
            naive_forecast = actual_array[:-1]  # Use previous value as naive forecast
            naive_errors = actual_array[1:] - naive_forecast
            naive_mse = np.mean(naive_errors**2)
            theils_u = rmse / np.sqrt(naive_mse) if naive_mse > 0 else float('inf')
        else:
            theils_u = float('inf')
        
        return {
            "mae": float(mae),
            "mse": float(mse),
            "rmse": float(rmse),
            "mape": float(mape),
            "smape": float(smape),
            "mbe": float(mbe),
            "correlation": float(correlation),
            "theils_u": float(theils_u),
            "sample_size": min_length
        }
        
    except Exception as e:
        logger.error(f"Error calculating forecast accuracy: {e}")
        return {"error": str(e)}


def calculate_directional_accuracy(forecast_values: List[float], actual_values: List[float]) -> Dict[str, Any]:
    """
    Calculate directional accuracy (whether forecast correctly predicts direction of change)
    
    Args:
        forecast_values: Predicted values
        actual_values: Actual observed values
        
    Returns:
        Dict with directional accuracy metrics
    """
    try:
        if len(forecast_values) < 2 or len(actual_values) < 2:
            return {"error": "Insufficient data for directional accuracy"}
        
        # Calculate changes
        forecast_changes = np.diff(forecast_values)
        actual_changes = np.diff(actual_values)
        
        # Determine directions (up, down, no change)
        forecast_directions = np.sign(forecast_changes)
        actual_directions = np.sign(actual_changes)
        
        # Count correct directions
        correct_directions = np.sum(forecast_directions == actual_directions)
        total_changes = len(forecast_directions)
        
        directional_accuracy = correct_directions / total_changes if total_changes > 0 else 0
        
        # Detailed breakdown
        up_predicted = np.sum(forecast_directions > 0)
        down_predicted = np.sum(forecast_directions < 0)
        no_change_predicted = np.sum(forecast_directions == 0)
        
        up_actual = np.sum(actual_directions > 0)
        down_actual = np.sum(actual_directions < 0)
        no_change_actual = np.sum(actual_directions == 0)
        
        return {
            "directional_accuracy": float(directional_accuracy),
            "correct_predictions": int(correct_directions),
            "total_predictions": int(total_changes),
            "predicted_distribution": {
                "up": int(up_predicted),
                "down": int(down_predicted),
                "no_change": int(no_change_predicted)
            },
            "actual_distribution": {
                "up": int(up_actual),
                "down": int(down_actual),
                "no_change": int(no_change_actual)
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating directional accuracy: {e}")
        return {"error": str(e)}


def calculate_forecast_intervals_coverage(forecast_data: List[Dict], actual_values: List[float]) -> Dict[str, Any]:
    """
    Calculate how often actual values fall within forecast confidence intervals
    
    Args:
        forecast_data: List of forecast dictionaries with bounds
        actual_values: Actual observed values
        
    Returns:
        Dict with interval coverage metrics
    """
    try:
        if not forecast_data or not actual_values:
            return {"error": "No data provided"}
        
        total_forecasts = min(len(forecast_data), len(actual_values))
        within_intervals = 0
        
        for i in range(total_forecasts):
            forecast = forecast_data[i]
            actual = actual_values[i]
            
            lower_bound = forecast.get('lower_bound', float('-inf'))
            upper_bound = forecast.get('upper_bound', float('inf'))
            
            if lower_bound <= actual <= upper_bound:
                within_intervals += 1
        
        coverage_rate = within_intervals / total_forecasts if total_forecasts > 0 else 0
        
        # Get confidence level from forecast data
        confidence_level = forecast_data[0].get('confidence_level', 0.95) if forecast_data else 0.95
        expected_coverage = confidence_level
        
        return {
            "coverage_rate": float(coverage_rate),
            "expected_coverage": float(expected_coverage),
            "within_intervals": int(within_intervals),
            "total_forecasts": int(total_forecasts),
            "coverage_difference": float(coverage_rate - expected_coverage)
        }
        
    except Exception as e:
        logger.error(f"Error calculating interval coverage: {e}")
        return {"error": str(e)}


def generate_forecast_report(forecast_results: Dict[str, Any], actual_data: pd.Series = None) -> Dict[str, Any]:
    """
    Generate comprehensive forecast performance report
    
    Args:
        forecast_results: Forecast results from WeatherForecaster
        actual_data: Optional actual data for validation
        
    Returns:
        Dict with comprehensive forecast report
    """
    try:
        report = {
            "forecast_summary": {
                "forecast_horizon": len(forecast_results.get("forecast_data", [])),
                "model_info": forecast_results.get("model_info", {}),
                "forecast_statistics": forecast_results.get("forecast_statistics", {})
            },
            "metadata": forecast_results.get("metadata", {})
        }
        
        # Add accuracy metrics if actual data is provided
        if actual_data is not None:
            forecast_values = [item["forecast_temp"] for item in forecast_results.get("forecast_data", [])]
            
            if len(forecast_values) > 0 and len(actual_data) > 0:
                # Basic accuracy metrics
                accuracy_metrics = calculate_forecast_accuracy(forecast_values, actual_data.tolist())
                report["accuracy_metrics"] = accuracy_metrics
                
                # Directional accuracy
                if len(forecast_values) > 1:
                    directional_metrics = calculate_directional_accuracy(forecast_values, actual_data.tolist())
                    report["directional_accuracy"] = directional_metrics
                
                # Interval coverage
                interval_coverage = calculate_forecast_intervals_coverage(
                    forecast_results.get("forecast_data", []), 
                    actual_data.tolist()
                )
                report["interval_coverage"] = interval_coverage
        
        # Performance assessment
        if "accuracy_metrics" in report:
            metrics = report["accuracy_metrics"]
            if "error" not in metrics:
                # Simple performance classification
                mae = metrics.get("mae", float('inf'))
                correlation = metrics.get("correlation", 0)
                
                if mae < 2.0 and correlation > 0.7:
                    performance = "Excellent"
                elif mae < 3.0 and correlation > 0.5:
                    performance = "Good"
                elif mae < 5.0 and correlation > 0.3:
                    performance = "Fair"
                else:
                    performance = "Poor"
                    report["performance_assessment"] = {
                    "overall_rating": performance,
                    "mae_rating": "Good" if mae < 3.0 else "Poor",
                    "correlation_rating": "Good" if correlation > 0.5 else "Poor",
                    "recommendation": get_performance_recommendation(mae, correlation)
                }
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating forecast report: {e}")
        return {"error": str(e)}


def get_performance_recommendation(mae: float, correlation: float) -> str:
    """
    Get recommendation based on performance metrics
    
    Args:
        mae: Mean Absolute Error
        correlation: Correlation coefficient
        
    Returns:
        str: Performance recommendation
    """
    if mae < 2.0 and correlation > 0.7:
        return "Excellent forecast quality. Model is highly reliable for decision making."
    elif mae < 3.0 and correlation > 0.5:
        return "Good forecast quality. Model is suitable for most applications."
    elif mae < 5.0 and correlation > 0.3:
        return "Fair forecast quality. Use with caution and consider trend rather than exact values."
    else:
        return "Poor forecast quality. Consider collecting more data or using alternative methods."


def compare_forecast_methods(forecasts_dict: Dict[str, List[float]], 
                           actual_values: List[float]) -> Dict[str, Any]:
    """
    Compare multiple forecasting methods
    
    Args:
        forecasts_dict: Dictionary with method names and their forecasts
        actual_values: Actual observed values
        
    Returns:
        Dict with comparison results
    """
    try:
        comparison_results = {}
        
        for method_name, forecast_values in forecasts_dict.items():
            accuracy_metrics = calculate_forecast_accuracy(forecast_values, actual_values)
            comparison_results[method_name] = accuracy_metrics
        
        # Find best method based on RMSE
        best_method = None
        best_rmse = float('inf')
        
        for method_name, metrics in comparison_results.items():
            if "error" not in metrics:
                rmse = metrics.get("rmse", float('inf'))
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_method = method_name
        
        return {
            "individual_results": comparison_results,
            "best_method": best_method,
            "best_rmse": best_rmse,
            "ranking": sorted(
                [(name, metrics.get("rmse", float('inf'))) 
                 for name, metrics in comparison_results.items() 
                 if "error" not in metrics],
                key=lambda x: x[1]
            )
        }
        
    except Exception as e:
        logger.error(f"Error comparing forecast methods: {e}")
        return {"error": str(e)}


def calculate_seasonal_accuracy(forecast_values: List[float], 
                              actual_values: List[float],
                              dates: List[str]) -> Dict[str, Any]:
    """
    Calculate accuracy metrics by season
    
    Args:
        forecast_values: Predicted values
        actual_values: Actual observed values
        dates: Corresponding dates
        
    Returns:
        Dict with seasonal accuracy metrics
    """
    try:
        import pandas as pd
        
        # Create DataFrame
        df = pd.DataFrame({
            'forecast': forecast_values,
            'actual': actual_values,
            'date': pd.to_datetime(dates)
        })
        
        # Add season column
        df['season'] = df['date'].dt.month.map({
            12: 'Winter', 1: 'Winter', 2: 'Winter',
            3: 'Spring', 4: 'Spring', 5: 'Spring',
            6: 'Summer', 7: 'Summer', 8: 'Summer',
            9: 'Autumn', 10: 'Autumn', 11: 'Autumn'
        })
        
        seasonal_results = {}
        
        for season in ['Spring', 'Summer', 'Autumn', 'Winter']:
            season_data = df[df['season'] == season]
            
            if len(season_data) > 0:
                seasonal_accuracy = calculate_forecast_accuracy(
                    season_data['forecast'].tolist(),
                    season_data['actual'].tolist()
                )
                seasonal_results[season] = seasonal_accuracy
            else:
                seasonal_results[season] = {"error": "No data for this season"}
        
        return seasonal_results
        
    except Exception as e:
        logger.error(f"Error calculating seasonal accuracy: {e}")
        return {"error": str(e)}


def calculate_forecast_skill_score(forecast_values: List[float], 
                                 actual_values: List[float],
                                 reference_forecast: List[float] = None) -> Dict[str, float]:
    """
    Calculate forecast skill score compared to a reference forecast
    
    Args:
        forecast_values: Predicted values
        actual_values: Actual observed values
        reference_forecast: Reference forecast (default: persistence/climatology)
        
    Returns:
        Dict with skill scores
    """
    try:
        # Calculate RMSE for main forecast
        main_metrics = calculate_forecast_accuracy(forecast_values, actual_values)
        main_rmse = main_metrics.get("rmse", float('inf'))
        
        # If no reference provided, use persistence (previous value)
        if reference_forecast is None:
            if len(actual_values) > 1:
                reference_forecast = [actual_values[0]] + actual_values[:-1]
            else:
                return {"error": "Insufficient data for skill score calculation"}
        
        # Calculate RMSE for reference forecast
        ref_metrics = calculate_forecast_accuracy(reference_forecast, actual_values)
        ref_rmse = ref_metrics.get("rmse", float('inf'))
        
        # Calculate skill score
        if ref_rmse > 0:
            skill_score = 1 - (main_rmse / ref_rmse)
        else:
            skill_score = 0
        
        return {
            "skill_score": float(skill_score),
            "forecast_rmse": main_rmse,
            "reference_rmse": ref_rmse,
            "interpretation": "Better than reference" if skill_score > 0 else "Worse than reference"
        }
        
    except Exception as e:
        logger.error(f"Error calculating skill score: {e}")
        return {"error": str(e)}


def analyze_forecast_bias(forecast_values: List[float], actual_values: List[float]) -> Dict[str, Any]:
    """
    Analyze forecast bias patterns
    
    Args:
        forecast_values: Predicted values
        actual_values: Actual observed values
        
    Returns:
        Dict with bias analysis
    """
    try:
        min_length = min(len(forecast_values), len(actual_values))
        forecast_array = np.array(forecast_values[:min_length])
        actual_array = np.array(actual_values[:min_length])
        
        errors = forecast_array - actual_array
        
        # Overall bias
        mean_bias = np.mean(errors)
        
        # Bias by temperature range
        low_temp_mask = actual_array < np.percentile(actual_array, 33)
        mid_temp_mask = (actual_array >= np.percentile(actual_array, 33)) & (actual_array < np.percentile(actual_array, 67))
        high_temp_mask = actual_array >= np.percentile(actual_array, 67)
        
        low_temp_bias = np.mean(errors[low_temp_mask]) if np.any(low_temp_mask) else 0
        mid_temp_bias = np.mean(errors[mid_temp_mask]) if np.any(mid_temp_mask) else 0
        high_temp_bias = np.mean(errors[high_temp_mask]) if np.any(high_temp_mask) else 0
        
        # Bias trend over time
        bias_trend = np.corrcoef(range(len(errors)), errors)[0, 1] if len(errors) > 1 else 0
        
        return {
            "overall_bias": float(mean_bias),
            "bias_by_temperature": {
                "low_temperatures": float(low_temp_bias),
                "mid_temperatures": float(mid_temp_bias),
                "high_temperatures": float(high_temp_bias)
            },
            "bias_trend": float(bias_trend),
            "bias_interpretation": {
                "overall": "Over-forecasting" if mean_bias > 0.5 else "Under-forecasting" if mean_bias < -0.5 else "Well-calibrated",
                "trend": "Increasing bias" if bias_trend > 0.1 else "Decreasing bias" if bias_trend < -0.1 else "Stable bias"
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing forecast bias: {e}")
        return {"error": str(e)}

