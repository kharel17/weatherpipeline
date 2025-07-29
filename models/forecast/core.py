"""
Core ARIMA Weather Forecasting
Main WeatherForecaster class for time series forecasting
"""

import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import warnings

# Statistical modeling
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logging.warning("statsmodels not available. Install with: pip install statsmodels")

# Suppress statsmodels warnings
warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")

logger = logging.getLogger(__name__)


class WeatherForecaster:
    """
    Core ARIMA weather forecasting class
    Handles model fitting, prediction, and validation
    """
    
    def __init__(self, default_order: Tuple[int, int, int] = (2, 1, 2)):
        """
        Initialize the weather forecaster
        
        Args:
            default_order: Default ARIMA order (p, d, q)
        """
        if not STATSMODELS_AVAILABLE:
            raise ImportError("statsmodels is required for forecasting. Install with: pip install statsmodels")
        
        self.default_order = default_order
        self.model = None
        self.fitted_model = None
        self.data_series = None
        self.forecast_results = None
        
        logger.info(f"WeatherForecaster initialized with ARIMA order {default_order}")
    
    def prepare_data(self, data: pd.Series, min_periods: int = 10) -> bool:
        """
        Prepare and validate time series data for forecasting
        
        Args:
            data: Time series data with datetime index
            min_periods: Minimum number of data points required
            
        Returns:
            bool: True if data is suitable for forecasting
        """
        try:
            if len(data) < min_periods:
                logger.error(f"Insufficient data: {len(data)} points (minimum {min_periods} required)")
                return False
            
            # Remove missing values
            self.data_series = data.dropna()
            
            if len(self.data_series) < min_periods:
                logger.error(f"Insufficient data after removing NaN: {len(self.data_series)} points")
                return False
            
            # Ensure datetime index
            if not isinstance(self.data_series.index, pd.DatetimeIndex):
                logger.error("Data must have datetime index")
                return False
            
            # Sort by date
            self.data_series = self.data_series.sort_index()
            
            # Check for reasonable temperature values
            if self.data_series.min() < -100 or self.data_series.max() > 70:
                logger.warning("Temperature values outside reasonable range detected")
            
            logger.info(f"Data prepared successfully: {len(self.data_series)} data points")
            logger.info(f"Date range: {self.data_series.index.min()} to {self.data_series.index.max()}")
            logger.info(f"Temperature range: {self.data_series.min():.1f}°C to {self.data_series.max():.1f}°C")
            
            return True
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return False
    
    def check_stationarity(self, significance_level: float = 0.05) -> Dict[str, Any]:
        """
        Check if the time series is stationary using Augmented Dickey-Fuller test
        
        Args:
            significance_level: Significance level for stationarity test
            
        Returns:
            Dict with stationarity test results
        """
        if self.data_series is None:
            return {"error": "No data prepared"}
        
        try:
            # Perform Augmented Dickey-Fuller test
            adf_result = adfuller(self.data_series)
            
            is_stationary = adf_result[1] <= significance_level
            
            result = {
                "is_stationary": is_stationary,
                "adf_statistic": adf_result[0],
                "p_value": adf_result[1],
                "critical_values": adf_result[4],
                "significance_level": significance_level,
                "interpretation": "Stationary" if is_stationary else "Non-stationary"
            }
            
            logger.info(f"Stationarity test: {result['interpretation']} (p-value: {result['p_value']:.4f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking stationarity: {e}")
            return {"error": str(e)}
    
    def auto_select_order(self, max_p: int = 5, max_d: int = 2, max_q: int = 5) -> Tuple[int, int, int]:
        """
        Automatically select optimal ARIMA order using AIC criterion
        
        Args:
            max_p: Maximum AR order to test
            max_d: Maximum differencing order to test
            max_q: Maximum MA order to test
            
        Returns:
            Tuple of optimal (p, d, q) order
        """
        if self.data_series is None:
            logger.error("No data prepared for order selection")
            return self.default_order
        
        try:
            logger.info("Selecting optimal ARIMA order...")
            
            best_aic = float('inf')
            best_order = self.default_order
            
            # Test different combinations
            for p in range(max_p + 1):
                for d in range(max_d + 1):
                    for q in range(max_q + 1):
                        try:
                            # Skip if no parameters
                            if p == 0 and d == 0 and q == 0:
                                continue
                            
                            model = ARIMA(self.data_series, order=(p, d, q))
                            fitted_model = model.fit()
                            aic = fitted_model.aic
                            
                            if aic < best_aic:
                                best_aic = aic
                                best_order = (p, d, q)
                                
                        except Exception:
                            continue
            
            logger.info(f"Optimal ARIMA order selected: {best_order} (AIC: {best_aic:.2f})")
            return best_order
            
        except Exception as e:
            logger.error(f"Error in auto order selection: {e}")
            return self.default_order
    
    def fit_model(self, order: Optional[Tuple[int, int, int]] = None, auto_select: bool = True) -> bool:
        """
        Fit ARIMA model to the prepared data
        
        Args:
            order: ARIMA order (p, d, q). If None, uses default or auto-selected
            auto_select: Whether to automatically select optimal order
            
        Returns:
            bool: True if model fitted successfully
        """
        if self.data_series is None:
            logger.error("No data prepared for model fitting")
            return False
        
        try:
            # Determine model order
            if auto_select and len(self.data_series) >= 20:
                model_order = self.auto_select_order()
            elif order:
                model_order = order
            else:
                model_order = self.default_order
            
            logger.info(f"Fitting ARIMA{model_order} model...")
            
            # Create and fit model
            self.model = ARIMA(self.data_series, order=model_order)
            self.fitted_model = self.model.fit()
            
            # Log model summary
            logger.info(f"Model fitted successfully")
            logger.info(f"AIC: {self.fitted_model.aic:.2f}")
            logger.info(f"BIC: {self.fitted_model.bic:.2f}")
            logger.info(f"Log Likelihood: {self.fitted_model.llf:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error fitting model: {e}")
            return False
    
    def generate_forecast(self, steps: int = 3, confidence_level: float = 0.95) -> Dict[str, Any]:
        """
        Generate weather forecast using the fitted ARIMA model
        
        Args:
            steps: Number of periods to forecast
            confidence_level: Confidence level for prediction intervals
            
        Returns:
            Dict with forecast results
        """
        if self.fitted_model is None:
            logger.error("No model fitted for forecasting")
            return {"error": "No model fitted"}
        
        try:
            logger.info(f"Generating {steps}-step forecast...")
            
            # Generate forecast
            forecast = self.fitted_model.forecast(steps=steps)
            conf_int = self.fitted_model.get_forecast(steps=steps).conf_int(alpha=1-confidence_level)
            
            # Create future dates
            last_date = self.data_series.index[-1]
            future_dates = [last_date + timedelta(days=i+1) for i in range(steps)]
            
            # Prepare forecast results
            forecast_data = []
            for i in range(steps):
                forecast_data.append({
                    "date": future_dates[i].strftime('%Y-%m-%d'),
                    "forecast_temp": round(float(forecast.iloc[i]), 1),
                    "lower_bound": round(float(conf_int.iloc[i, 0]), 1),
                    "upper_bound": round(float(conf_int.iloc[i, 1]), 1),
                    "confidence_level": confidence_level
                })
            
            # Calculate forecast statistics
            forecast_mean = float(forecast.mean())
            forecast_std = float(forecast.std())
            
            # Historical comparison
            historical_mean = float(self.data_series.mean())
            historical_std = float(self.data_series.std())
            
            self.forecast_results = {
                "forecast_data": forecast_data,
                "forecast_statistics": {
                    "forecast_mean": forecast_mean,
                    "forecast_std": forecast_std,
                    "historical_mean": historical_mean,
                    "historical_std": historical_std,
                    "trend_direction": "increasing" if forecast_data[-1]["forecast_temp"] > forecast_data[0]["forecast_temp"] else "decreasing"
                },
                "model_info": {
                    "arima_order": self.fitted_model.model.order,
                    "aic": self.fitted_model.aic,
                    "confidence_level": confidence_level,
                    "forecast_horizon": steps
                },
                "metadata": {
                    "forecast_generated_at": datetime.utcnow().isoformat(),
                    "data_points_used": len(self.data_series),
                    "data_date_range": {
                        "start": self.data_series.index.min().strftime('%Y-%m-%d'),
                        "end": self.data_series.index.max().strftime('%Y-%m-%d')
                    }
                }
            }
            
            logger.info(f"Forecast generated successfully")
            logger.info(f"Mean forecast temperature: {forecast_mean:.1f}°C")
            logger.info(f"Temperature trend: {self.forecast_results['forecast_statistics']['trend_direction']}")
            
            return self.forecast_results
            
        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return {"error": str(e)}
    
    def get_model_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive model summary
        
        Returns:
            Dict with model information and diagnostics
        """
        if self.fitted_model is None:
            return {"error": "No model fitted"}
        
        try:
            # Get model parameters
            params = self.fitted_model.params
            
            summary = {
                "model_order": self.fitted_model.model.order,
                "parameters": {
                    "ar_params": params.filter(regex='^ar').to_dict(),
                    "ma_params": params.filter(regex='^ma').to_dict(),
                    "const": params.get('const', 0.0)
                },
                "information_criteria": {
                    "aic": self.fitted_model.aic,
                    "bic": self.fitted_model.bic,
                    "hqic": self.fitted_model.hqic
                },
                "goodness_of_fit": {
                    "log_likelihood": self.fitted_model.llf,
                    "sigma2": self.fitted_model.sigma2
                },
                "data_info": {
                    "observations": len(self.data_series),
                    "date_range": {
                        "start": self.data_series.index.min().strftime('%Y-%m-%d'),
                        "end": self.data_series.index.max().strftime('%Y-%m-%d')
                    }
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting model summary: {e}")
            return {"error": str(e)}