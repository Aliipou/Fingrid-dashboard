# backend/app/api/routes/analytics.py
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from app.services.fingrid_service import fingrid_service
from app.services.cache_service import cache_service
from app.models.energy import EnergyData, DatasetType
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class AnalyticsService:
    """Advanced analytics service for energy data"""
    
    def __init__(self):
        self.cache_ttl = 1800  # 30 minutes for analytics
    
    async def calculate_efficiency_metrics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate energy efficiency metrics"""
        try:
            # Get consumption and production data
            consumption_data = await fingrid_service.get_consumption_realtime(
                start_date, end_date
            )
            production_data = await fingrid_service.get_production_realtime(
                start_date, end_date
            )
            
            if not consumption_data.data or not production_data.data:
                raise HTTPException(
                    status_code=404, 
                    detail="Insufficient data for efficiency calculation"
                )
            
            # Convert to pandas for analysis
            consumption_df = pd.DataFrame([
                {"timestamp": point.timestamp, "value": point.value}
                for point in consumption_data.data
            ])
            
            production_df = pd.DataFrame([
                {"timestamp": point.timestamp, "value": point.value}
                for point in production_data.data
            ])
            
            # Merge dataframes
            merged_df = pd.merge(
                consumption_df, production_df, 
                on="timestamp", suffixes=("_consumption", "_production")
            )
            
            # Calculate metrics
            total_consumption = merged_df["value_consumption"].sum()
            total_production = merged_df["value_production"].sum()
            
            efficiency_ratio = (total_production / total_consumption) * 100
            surplus_hours = len(merged_df[
                merged_df["value_production"] > merged_df["value_consumption"]
            ])
            deficit_hours = len(merged_df[
                merged_df["value_production"] < merged_df["value_consumption"]
            ])
            
            # Peak analysis
            consumption_peak = merged_df["value_consumption"].max()
            consumption_peak_time = merged_df[
                merged_df["value_consumption"] == consumption_peak
            ]["timestamp"].iloc[0]
            
            production_peak = merged_df["value_production"].max()
            production_peak_time = merged_df[
                merged_df["value_production"] == production_peak
            ]["timestamp"].iloc[0]
            
            # Variability analysis
            consumption_std = merged_df["value_consumption"].std()
            production_std = merged_df["value_production"].std()
            
            consumption_cv = (consumption_std / merged_df["value_consumption"].mean()) * 100
            production_cv = (production_std / merged_df["value_production"].mean()) * 100
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "duration_hours": len(merged_df)
                },
                "totals": {
                    "consumption_mwh": round(total_consumption, 2),
                    "production_mwh": round(total_production, 2),
                    "net_balance_mwh": round(total_production - total_consumption, 2)
                },
                "efficiency": {
                    "production_consumption_ratio": round(efficiency_ratio, 2),
                    "surplus_hours": surplus_hours,
                    "deficit_hours": deficit_hours,
                    "balanced_hours": len(merged_df) - surplus_hours - deficit_hours
                },
                "peaks": {
                    "consumption_peak_mw": round(consumption_peak, 2),
                    "consumption_peak_time": consumption_peak_time.isoformat(),
                    "production_peak_mw": round(production_peak, 2), 
                    "production_peak_time": production_peak_time.isoformat()
                },
                "variability": {
                    "consumption_coefficient_variation": round(consumption_cv, 2),
                    "production_coefficient_variation": round(production_cv, 2),
                    "consumption_standard_deviation": round(consumption_std, 2),
                    "production_standard_deviation": round(production_std, 2)
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating efficiency metrics: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Analytics calculation failed: {str(e)}"
            )
    
    async def detect_anomalies(
        self, 
        dataset_type: DatasetType,
        start_date: datetime, 
        end_date: datetime,
        threshold_std: float = 2.0
    ) -> Dict[str, Any]:
        """Detect anomalies in energy data using statistical methods"""
        try:
            # Get data based on type
            if dataset_type == DatasetType.CONSUMPTION_REALTIME:
                data = await fingrid_service.get_consumption_realtime(start_date, end_date)
            elif dataset_type == DatasetType.PRODUCTION_REALTIME:
                data = await fingrid_service.get_production_realtime(start_date, end_date)
            elif dataset_type == DatasetType.WIND_PRODUCTION:
                data = await fingrid_service.get_wind_production(start_date, end_date)
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported dataset type for anomaly detection: {dataset_type}"
                )
            
            if not data.data:
                raise HTTPException(status_code=404, detail="No data available")
            
            # Convert to pandas
            df = pd.DataFrame([
                {"timestamp": point.timestamp, "value": point.value}
                for point in data.data
            ])
            
            # Calculate statistical parameters
            mean_value = df["value"].mean()
            std_value = df["value"].std()
            
            # Define anomaly thresholds
            upper_threshold = mean_value + (threshold_std * std_value)
            lower_threshold = mean_value - (threshold_std * std_value)
            
            # Detect anomalies
            anomalies = df[
                (df["value"] > upper_threshold) | (df["value"] < lower_threshold)
            ]
            
            # Additional analysis
            consecutive_anomalies = []
            if len(anomalies) > 1:
                anomalies_sorted = anomalies.sort_values("timestamp")
                current_group = [anomalies_sorted.iloc[0]]
                
                for i in range(1, len(anomalies_sorted)):
                    time_diff = (
                        anomalies_sorted.iloc[i]["timestamp"] - 
                        anomalies_sorted.iloc[i-1]["timestamp"]
                    ).total_seconds() / 3600  # hours
                    
                    if time_diff <= 1:  # Within 1 hour
                        current_group.append(anomalies_sorted.iloc[i])
                    else:
                        if len(current_group) > 1:
                            consecutive_anomalies.append(current_group)
                        current_group = [anomalies_sorted.iloc[i]]
                
                if len(current_group) > 1:
                    consecutive_anomalies.append(current_group)
            
            return {
                "dataset_type": dataset_type,
                "analysis_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "parameters": {
                    "threshold_standard_deviations": threshold_std,
                    "mean_value": round(mean_value, 2),
                    "standard_deviation": round(std_value, 2),
                    "upper_threshold": round(upper_threshold, 2),
                    "lower_threshold": round(lower_threshold, 2)
                },
                "anomalies": [
                    {
                        "timestamp": anomaly["timestamp"].isoformat(),
                        "value": round(anomaly["value"], 2),
                        "deviation_from_mean": round(anomaly["value"] - mean_value, 2),
                        "severity": "high" if abs(anomaly["value"] - mean_value) > (3 * std_value) else "medium"
                    }
                    for _, anomaly in anomalies.iterrows()
                ],
                "summary": {
                    "total_data_points": len(df),
                    "anomalies_detected": len(anomalies),
                    "anomaly_percentage": round((len(anomalies) / len(df)) * 100, 2),
                    "consecutive_anomaly_groups": len(consecutive_anomalies),
                    "max_consecutive_anomalies": max([len(group) for group in consecutive_anomalies]) if consecutive_anomalies else 0
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Anomaly detection failed: {str(e)}"
            )
    
    async def forecast_accuracy_analysis(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze forecast accuracy by comparing predictions with actual consumption"""
        try:
            # Get forecast and actual data
            forecast_data = await fingrid_service.get_consumption_forecast(start_date, end_date)
            actual_data = await fingrid_service.get_consumption_realtime(start_date, end_date)
            
            if not forecast_data.data or not actual_data.data:
                raise HTTPException(
                    status_code=404, 
                    detail="Insufficient data for forecast analysis"
                )
            
            # Convert to pandas
            forecast_df = pd.DataFrame([
                {"timestamp": point.timestamp, "forecast": point.value}
                for point in forecast_data.data
            ])
            
            actual_df = pd.DataFrame([
                {"timestamp": point.timestamp, "actual": point.value}
                for point in actual_data.data
            ])
            
            # Merge dataframes on timestamp
            merged_df = pd.merge(forecast_df, actual_df, on="timestamp")
            
            if len(merged_df) == 0:
                raise HTTPException(
                    status_code=404, 
                    detail="No matching timestamps between forecast and actual data"
                )
            
            # Calculate accuracy metrics
            merged_df["error"] = merged_df["forecast"] - merged_df["actual"]
            merged_df["absolute_error"] = abs(merged_df["error"])
            merged_df["percentage_error"] = (merged_df["error"] / merged_df["actual"]) * 100
            merged_df["absolute_percentage_error"] = abs(merged_df["percentage_error"])
            
            # Statistical metrics
            mae = merged_df["absolute_error"].mean()  # Mean Absolute Error
            mape = merged_df["absolute_percentage_error"].mean()  # Mean Absolute Percentage Error
            rmse = np.sqrt((merged_df["error"] ** 2).mean())  # Root Mean Square Error
            bias = merged_df["error"].mean()  # Forecast bias
            
            # Time-based analysis
            merged_df["hour"] = merged_df["timestamp"].dt.hour
            hourly_accuracy = merged_df.groupby("hour")["absolute_percentage_error"].mean()
            
            best_hour = hourly_accuracy.idxmin()
            worst_hour = hourly_accuracy.idxmax()
            
            return {
                "analysis_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "data_points": len(merged_df)
                },
                "accuracy_metrics": {
                    "mean_absolute_error_mw": round(mae, 2),
                    "mean_absolute_percentage_error": round(mape, 2),
                    "root_mean_square_error_mw": round(rmse, 2),
                    "forecast_bias_mw": round(bias, 2),
                    "bias_direction": "over-forecast" if bias > 0 else "under-forecast"
                },
                "time_analysis": {
                    "best_forecast_hour": int(best_hour),
                    "best_hour_mape": round(hourly_accuracy[best_hour], 2),
                    "worst_forecast_hour": int(worst_hour),
                    "worst_hour_mape": round(hourly_accuracy[worst_hour], 2)
                },
                "distribution": {
                    "error_std_deviation": round(merged_df["error"].std(), 2),
                    "percentage_within_5_percent": round(
                        (len(merged_df[merged_df["absolute_percentage_error"] <= 5]) / len(merged_df)) * 100, 2
                    ),
                    "percentage_within_10_percent": round(
                        (len(merged_df[merged_df["absolute_percentage_error"] <= 10]) / len(merged_df)) * 100, 2
                    )
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing forecast accuracy: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Forecast accuracy analysis failed: {str(e)}"
            )

# Initialize service
analytics_service = AnalyticsService()

# API Endpoints
@router.get("/efficiency")
async def get_efficiency_metrics(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis")
):
    """Get energy efficiency metrics for the specified period"""
    cache_key = f"efficiency:{start_date.isoformat()}:{end_date.isoformat()}"
    
    # Try cache first
    cached_result = await cache_service.get(cache_key)
    if cached_result:
        return JSONResponse(content=cached_result)
    
    result = await analytics_service.calculate_efficiency_metrics(start_date, end_date)
    
    # Cache result
    await cache_service.set(cache_key, result, ttl=analytics_service.cache_ttl)
    
    return JSONResponse(content=result)

@router.get("/anomalies")
async def detect_anomalies(
    dataset_type: DatasetType = Query(..., description="Type of dataset to analyze"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    threshold: float = Query(2.0, description="Standard deviation threshold for anomaly detection")
):
    """Detect anomalies in energy data"""
    cache_key = f"anomalies:{dataset_type}:{start_date.isoformat()}:{end_date.isoformat()}:{threshold}"
    
    # Try cache first
    cached_result = await cache_service.get(cache_key)
    if cached_result:
        return JSONResponse(content=cached_result)
    
    result = await analytics_service.detect_anomalies(
        dataset_type, start_date, end_date, threshold
    )
    
    # Cache result
    await cache_service.set(cache_key, result, ttl=analytics_service.cache_ttl)
    
    return JSONResponse(content=result)

@router.get("/forecast-accuracy")
async def analyze_forecast_accuracy(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis")
):
    """Analyze forecast accuracy by comparing predictions with actual consumption"""
    cache_key = f"forecast_accuracy:{start_date.isoformat()}:{end_date.isoformat()}"
    
    # Try cache first
    cached_result = await cache_service.get(cache_key)
    if cached_result:
        return JSONResponse(content=cached_result)
    
    result = await analytics_service.forecast_accuracy_analysis(start_date, end_date)
    
    # Cache result
    await cache_service.set(cache_key, result, ttl=analytics_service.cache_ttl)
    
    return JSONResponse(content=result)

@router.get("/trends")
async def analyze_trends(
    dataset_type: DatasetType = Query(..., description="Type of dataset to analyze"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    period: str = Query("daily", description="Aggregation period: hourly, daily, weekly")
):
    """Analyze trends in energy data over time"""
    try:
        # Get data based on type
        if dataset_type == DatasetType.CONSUMPTION_REALTIME:
            data = await fingrid_service.get_consumption_realtime(start_date, end_date)
        elif dataset_type == DatasetType.PRODUCTION_REALTIME:
            data = await fingrid_service.get_production_realtime(start_date, end_date)
        elif dataset_type == DatasetType.WIND_PRODUCTION:
            data = await fingrid_service.get_wind_production(start_date, end_date)
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported dataset type: {dataset_type}"
            )
        
        if not data.data:
            raise HTTPException(status_code=404, detail="No data available")
        
        # Convert to pandas
        df = pd.DataFrame([
            {"timestamp": point.timestamp, "value": point.value}
            for point in data.data
        ])
        
        # Set timestamp as index
        df.set_index("timestamp", inplace=True)
        
        # Resample based on period
        if period == "hourly":
            resampled = df.resample("H").mean()
        elif period == "daily":
            resampled = df.resample("D").mean()
        elif period == "weekly":
            resampled = df.resample("W").mean()
        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid period. Use: hourly, daily, or weekly"
            )
        
        # Calculate trend metrics
        values = resampled["value"].values
        
        # Linear trend calculation
        from scipy import stats
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        # Calculate moving averages
        ma_short = resampled["value"].rolling(window=min(7, len(resampled))).mean()
        ma_long = resampled["value"].rolling(window=min(30, len(resampled))).mean()
        
        return {
            "dataset_type": dataset_type,
            "period": period,
            "analysis_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "data_points": len(resampled)
            },
            "trend_analysis": {
                "slope_per_period": round(slope, 4),
                "trend_direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
                "correlation_coefficient": round(r_value, 4),
                "statistical_significance": round(p_value, 4),
                "trend_strength": "strong" if abs(r_value) > 0.7 else "moderate" if abs(r_value) > 0.3 else "weak"
            },
            "summary_statistics": {
                "mean": round(resampled["value"].mean(), 2),
                "median": round(resampled["value"].median(), 2),
                "std_deviation": round(resampled["value"].std(), 2),
                "min_value": round(resampled["value"].min(), 2),
                "max_value": round(resampled["value"].max(), 2),
                "range": round(resampled["value"].max() - resampled["value"].min(), 2)
            },
            "moving_averages": {
                "short_term_current": round(ma_short.iloc[-1], 2) if not ma_short.empty else None,
                "long_term_current": round(ma_long.iloc[-1], 2) if not ma_long.empty else None,
                "signal": "bullish" if (not ma_short.empty and not ma_long.empty and ma_short.iloc[-1] > ma_long.iloc[-1]) else "bearish"
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing trends: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Trend analysis failed: {str(e)}"
        )