"""
Model Validation for Weather Forecasting
Statistical tests and validation methods for ARIMA models
"""

import pandas as pd
import logging
from typing import Dict, Any

try:
    from statsmodels.stats.diagnostic import acorr_ljungbox
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

logger = logging.getLogger(__name__)


def validate_arima_model(fitted_model) -> Dict[str, Any]:
    """
    Validate the fitted ARIMA model using residual analysis
    
    Args:
        fitted_model: Fitted ARIMA model from statsmodels
        
    Returns:
        Dict with validation results
    """
    if fitted_model is None:
        return {"error": "No model provided"}
    
    if not STATSMODELS_AVAILABLE:
        return {"error": "statsmodels not available for validation"}
    
    try:
        # Get residuals
        residuals = fitted_model.resid
        
        # Ljung-Box test for residual autocorrelation
        lb_test = acorr_ljungbox(residuals, lags=10, return_df=True)
        
        # Residual statistics
        validation_results = {
            "residual_mean": float(residuals.mean()),
            "residual_std": float(residuals.std()),
            "residual_min": float(residuals.min()),
            "residual_max": float(residuals.max()),
            "ljung_box_p_values": lb_test['lb_pvalue'].to_dict(),
            "model_aic": fitted_model.aic,
            "model_bic": fitted_model.bic,
            "log_likelihood": fitted_model.llf
        }
        
        # Check if residuals are white noise (good model)
        significant_autocorr = (lb_test['lb_pvalue'] < 0.05).any()
        validation_results["has_autocorrelation"] = significant_autocorr
        validation_results["validation_status"] = "Poor" if significant_autocorr else "Good"
        
        logger.info(f"Model validation: {validation_results['validation_status']}")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Error validating model: {e}")
        return {"error": str(e)}


def check_residual_normality(fitted_model) -> Dict[str, Any]:
    """
    Check if model residuals are normally distributed
    
    Args:
        fitted_model: Fitted ARIMA model
        
    Returns:
        Dict with normality test results
    """
    try:
        residuals = fitted_model.resid
        
        # Basic normality checks
        from scipy import stats
        
        # Shapiro-Wilk test (for small samples)
        if len(residuals) <= 50:
            shapiro_stat, shapiro_p = stats.shapiro(residuals)
            normality_test = {
                "test": "Shapiro-Wilk",
                "statistic": float(shapiro_stat),
                "p_value": float(shapiro_p),
                "is_normal": shapiro_p > 0.05
            }
        else:
            # Kolmogorov-Smirnov test (for larger samples)
            ks_stat, ks_p = stats.kstest(residuals, 'norm')
            normality_test = {
                "test": "Kolmogorov-Smirnov",
                "statistic": float(ks_stat),
                "p_value": float(ks_p),
                "is_normal": ks_p > 0.05
            }
        
        # Additional statistics
        skewness = float(stats.skew(residuals))
        kurtosis = float(stats.kurtosis(residuals))
        
        return {
            "normality_test": normality_test,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "interpretation": "Normal" if normality_test["is_normal"] else "Non-normal"
        }
        
    except Exception as e:
        logger.error(f"Error checking residual normality: {e}")
        return {"error": str(e)}


def validate_forecast_assumptions(data_series: pd.Series) -> Dict[str, Any]:
    """
    Validate assumptions for time series forecasting
    
    Args:
        data_series: Time series data
        
    Returns:
        Dict with assumption validation results
    """
    try:
        validation_results = {
            "data_length": len(data_series),
            "missing_values": data_series.isnull().sum(),
            "data_range": {
                "min": float(data_series.min()),
                "max": float(data_series.max()),
                "mean": float(data_series.mean()),
                "std": float(data_series.std())
            }
        }
        
        # Check for sufficient data
        validation_results["sufficient_data"] = len(data_series) >= 10
        
        # Check for reasonable values
        reasonable_range = (-50 <= data_series.min() <= 50) and (-50 <= data_series.max() <= 50)
        validation_results["reasonable_values"] = reasonable_range
        
        # Check for variance
        has_variance = data_series.std() > 0.1
        validation_results["has_variance"] = has_variance
        
        # Overall assessment
        all_checks = [
            validation_results["sufficient_data"],
            validation_results["reasonable_values"],
            validation_results["has_variance"],
            validation_results["missing_values"] == 0
        ]
        
        validation_results["overall_valid"] = all(all_checks)
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Error validating forecast assumptions: {e}")
        return {"error": str(e)}