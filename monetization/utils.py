import os
import pickle
import dill
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.conf import settings
from django.utils.timezone import make_aware
from weather.models import WeatherData
from monetization.models import CropSuitability

# NEW: Setup for Open-Meteo Archive API with caching and retries
import openmeteo_requests
import requests_cache
from retry_requests import retry

cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo_client = openmeteo_requests.Client(session=retry_session)

# monetization/utils.py
from django.utils.timezone import now
from monetization.models import Subscription

def has_active_subscription(user):
    """
    Returns True if the user has an active subscription or a canceled one that is still valid
    (i.e. until the next billing date).
    """
    return Subscription.objects.filter(
        user=user,
        status__in=["active", "canceled"],
        next_billing_date__gte=now()
    ).exists()


def get_historical_weather_data(lat, lon, start_date, end_date):
    """
    Pulls historical weather data from the Open-Meteo archive API
    for the given location and date range, and computes:
      - avg_max_temp: average of daily maximum temperatures
      - avg_min_temp: average of daily minimum temperatures
      - total_precip: total precipitation over the period
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "precipitation"
        ]),
        "timezone": "auto"
    }
    try:
        responses = openmeteo_client.weather_api("https://archive-api.open-meteo.com/v1/archive", params=params)
        if isinstance(responses, list) and responses:
            response = responses[0]
            hourly = response.Hourly()
            # Build DataFrame from hourly data
            times = pd.to_datetime(hourly.Time(), unit="s", utc=True)
            df = pd.DataFrame({
                "time": times,
                "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
                "precipitation": hourly.Variables(3).ValuesAsNumpy()
            })
            df["date"] = df["time"].dt.date
            # Compute daily maximum, minimum, and sum of precipitation
            daily = df.groupby("date").agg({
                "temperature_2m": ["max", "min"],
                "precipitation": "sum"
            })
            daily.columns = ["max_temp", "min_temp", "total_precip"]
            avg_max_temp = daily["max_temp"].mean()
            avg_min_temp = daily["min_temp"].mean()
            total_precip = df["precipitation"].sum()
            return {
                "avg_max_temp": avg_max_temp,
                "avg_min_temp": avg_min_temp,
                "total_precip": total_precip
            }
    except Exception as e:
        print("Error fetching historical weather data:", e)
    return None

# --- Model & Pipeline Loading ---
def load_model(model_name):
    model_path = os.path.join(settings.TRAINED_MODELS_DIR, model_name)
    with open(model_path, "rb") as file:
        return pickle.load(file)

def load_pipeline(pipeline_name):
    pipeline_path = os.path.join(settings.TRAINED_MODELS_DIR, pipeline_name)
    with open(pipeline_path, "rb") as file:
        return dill.load(file)

pipeline = load_pipeline("feature_engineering_pipeline.pkl")
models = {
    "linear_regression": load_model("linear_regression_model.pkl"),
    "decision_tree": load_model("decision_tree_model.pkl")
}

# --- Geolocation & Weather Functions ---
def get_lat_long(location):
    API_KEY = settings.OPENCAGE_API_KEY
    url = f"https://api.opencagedata.com/geocode/v1/json?q={location}&key={API_KEY}"
    response = requests.get(url).json()
    if response["results"]:
        return response["results"][0]["geometry"]["lat"], response["results"][0]["geometry"]["lng"]
    return None, None

def get_soil_temp(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=soil_temperature_0cm"
    response = requests.get(url).json()
    return response["hourly"]["soil_temperature_0cm"][-1] if "hourly" in response else None

def get_weather_data(lat, lon):
    """
    Returns either the most recent WeatherData from the database (if within the last day)
    OR the latest forecast data from Open-Meteo.
    """
    existing_data = WeatherData.objects.filter(latitude=lat, longitude=lon).order_by("-time").first()
    if existing_data and existing_data.time > make_aware(datetime.now()) - timedelta(days=1):
        return {
            "temperature_2m": existing_data.temperature_2m,
            "relative_humidity_2m": existing_data.relative_humidity_2m,
            "wind_speed_10m": existing_data.wind_speed_10m,
            "precipitation": existing_data.precipitation
        }
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"
    response = requests.get(url).json()
    return {
        "temperature_2m": response["hourly"]["temperature_2m"][-1],
        "relative_humidity_2m": response["hourly"]["relative_humidity_2m"][-1],
        "wind_speed_10m": response["hourly"]["wind_speed_10m"][-1],
        "precipitation": response["hourly"]["precipitation"][-1]
    } if "hourly" in response else None

# --- AI Soil Temperature Prediction ---
def predict_soil_temperature(user_data):
    """Predicts soil temperature using trained AI models."""
    input_df = pd.DataFrame([{
        "time": user_data.get("created_at", "2025-02-21 09:30:00"),
        "temperature_2m": user_data.get("temperature_2m", 20),
        "relative_humidity_2m": user_data.get("relative_humidity_2m", 80),
        "wind_speed_10m": user_data.get("wind_speed_10m", 5),
        "precipitation": user_data.get("precipitation", 1.0),
    }])
    engineered_data = pipeline.transform(input_df)
    required_features = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precip_30day_sum"]
    if "precip_30day_sum" not in engineered_data.columns:
        engineered_data["precip_30day_sum"] = engineered_data["precipitation"].rolling(window=30, min_periods=1).sum()
    engineered_data = engineered_data[required_features]
    predictions = {
        "linear_regression": models["linear_regression"].predict(engineered_data)[0],
        "decision_tree": models["decision_tree"].predict(engineered_data)[0]
    }
    return predictions

# --- Additional Premium Features ---
def forecast_future_climate(current_soil_temp):
    """Dummy function to simulate future soil temperature predictions."""
    forecast_30d = round(current_soil_temp + np.random.uniform(-1, 2), 1)
    forecast_60d = round(current_soil_temp + np.random.uniform(-2, 3), 1)
    forecast_90d = round(current_soil_temp + np.random.uniform(-3, 4), 1)
    return {
        "30_days": forecast_30d,
        "60_days": forecast_60d,
        "90_days": forecast_90d
    }

def calculate_crop_feasibility_score(crop, soil_data):
    """
    Refined feasibility:
      - Heavier penalty if BOTH pH & temperature are out of range
      - Incorporate moisture penalty
    """
    score = 100
    ph = soil_data.get("ph_level", 6.5)
    min_pH = crop.attributes.get("min_pH", 5.5)
    max_pH = crop.attributes.get("max_pH", 7.5)
    temp = soil_data.get("predicted_soil_temp", 20)
    min_temp = crop.attributes.get("min_temp", 10)
    max_temp = crop.attributes.get("max_temp", 35)
    moisture = soil_data.get("moisture", 50)

    pH_out = False
    temp_out = False
    if ph < min_pH or ph > max_pH:
        dist_p = abs(ph - min_pH) if ph < min_pH else abs(ph - max_pH)
        score -= dist_p * 15
        pH_out = True
    if temp < min_temp or temp > max_temp:
        dist_t = abs(temp - min_temp) if temp < min_temp else abs(temp - max_temp)
        score -= dist_t * 5
        temp_out = True
    if pH_out and temp_out:
        score -= 20
    if moisture < 30:
        score -= (30 - moisture) * 0.5
    elif moisture > 80:
        score -= (moisture - 80) * 0.5
    score = max(0, min(score, 100))
    return int(score)

def generate_crop_rotation_plan(recommended_crops):
    if not recommended_crops:
        return "No rotation plan available (no recommended crops)."
    plan_parts = []
    for idx, crop_name in enumerate(recommended_crops, start=1):
        plan_parts.append(f"{crop_name} (Season {idx})")
    plan_parts.append("Cover Crops (Off-Season)")
    plan = " → ".join(plan_parts)
    return f"Optimal Crop Rotation Cycle: {plan}"

# --- Dynamic Crop Suitability & Recommendations ---
def get_suitable_crops(soil_data):
    suitable_crops = []
    for crop in CropSuitability.objects.all():
        if "soil_type" in soil_data:
            if soil_data["soil_type"] not in [s.lower() for s in crop.suitable_soil_types]:
                continue
        crop_conditions = crop.attributes
        numeric_match = True
        for key in soil_data:
            if key in crop_conditions and key != "soil_type":
                val = soil_data[key]
                min_val = crop_conditions[key].get("min", float('-inf'))
                max_val = crop_conditions[key].get("max", float('inf'))
                if not (min_val <= val <= max_val):
                    numeric_match = False
                    break
        if numeric_match:
            suitable_crops.append(crop.name)
    return suitable_crops

def get_recommended_crops(soil_temp, ph_level, precipitation, soil_type):
    soil_data = {
        "temperature_2m": soil_temp,
        "ph_level": ph_level,
        "precipitation": precipitation,
        "soil_type": soil_type.lower()
    }
    return get_suitable_crops(soil_data)

# --- Dynamic Risk Assessment ---
RISK_THRESHOLDS = {
    "ph_level": {"low": 5.5, "high": 7.5, "low_msg": "⚠ Soil too acidic – Add lime.", "high_msg": "⚠ Soil too alkaline – Add sulfur."},
    "nitrogen": {"low": 30, "high": 80, "low_msg": "⚠ Low nitrogen – Apply nitrogen-rich fertilizer.", "high_msg": "⚠ High nitrogen – Monitor for excess foliage growth."}
}

def evaluate_soil_risks(soil_data):
    risks = []
    for param, limits in RISK_THRESHOLDS.items():
        if param in soil_data:
            value = soil_data[param]
            if "low" in limits and value < limits["low"]:
                risks.append(limits["low_msg"])
            if "high" in limits and value > limits["high"]:
                risks.append(limits["high_msg"])
    return risks if risks else ["✅ No major soil risks detected."]

def generate_risk_assessment(data):
    return evaluate_soil_risks(data)

# --- AI Alerts & Mitigation ---
def generate_ai_alerts(weather_data):
    alerts = []
    if weather_data["wind_speed_10m"] > 17:
        alerts.append("🌬️ Winds above 17 m/s detected. Windbreaks needed if sustained over 3+ days.")
    if weather_data["precipitation"] > 100:
        alerts.append("🌧️ Heavy rainfall detected – Improve drainage to prevent overwatering.")
    return alerts if alerts else ["✅ No major AI warnings detected."]

def generate_mitigation_strategies(soil_data):
    strategies = []
    pH = soil_data.get("ph_level", 6.5)
    nitrogen_val = soil_data.get("nitrogen", 50)
    moisture = soil_data.get("moisture", 35)
    if pH < 5.5:
        strategies.append(
            f"Apply 1–2 tons/acre of lime to raise soil pH from {pH} to at least 5.5–6.0. "
            "Re-test pH in 3 months. Consider gypsum if high aluminum is present."
        )
    elif pH > 7.5:
        strategies.append(
            "Apply elemental sulfur (e.g., 200 kg/ha) or organic matter to lower soil pH. "
            "Re-check pH in 2 months."
        )
    if nitrogen_val < 30:
        strategies.append(
            "Soil nitrogen is low. Apply ~40 kg/ha of Urea or Ammonium Sulfate. "
            "Consider intercropping with legumes."
        )
    if moisture < 30:
        strategies.append("Soil moisture is below optimal. Increase irrigation frequency or use drip irrigation.")
    elif moisture > 70:
        strategies.append("Soil moisture is high. Improve drainage or reduce watering intervals to prevent root rot.")
    strategies.append("For strong winds, plant windbreak trees (e.g., poplars) or use cover crops to protect seedlings.")
    return strategies if strategies else ["✅ No specific mitigation strategies required."]

def generate_next_best_action(soil_data, suitable_crops):
    if suitable_crops:
        action = f"✅ Primary Recommended Crop: {suitable_crops[0]}"
        if len(suitable_crops) > 1:
            action += f"\n🔹 Alternative Crop: {suitable_crops[1]}"
    else:
        action = "⚠ No recommended crops found. Improve soil conditions before planting."
    return action

def check_crop_feasibility(user_crop, soil_data):
    ideal_conditions = {
        "banana": {"ideal_temp": 25, "ideal_ph": 6.0},
        "potato": {"temp_range": (10, 25), "ph_range": (5.0, 6.0)},
        "corn": {"temp_range": (12, 30), "ph_range": (5.5, 7.5)},
    }
    crop_lower = user_crop.lower()
    soil_temp = soil_data.get("predicted_soil_temp", None)
    ph = soil_data.get("ph_level", None)
    if crop_lower not in ideal_conditions:
        return ""
    if crop_lower == "corn":
        conditions = ideal_conditions["corn"]
        temp_range = conditions["temp_range"]
        ph_range = conditions["ph_range"]
        messages = []
        if soil_temp is not None:
            if soil_temp < temp_range[0] or soil_temp > temp_range[1]:
                messages.append(
                    f"Corn prefers {temp_range[0]}–{temp_range[1]}°C, but your soil is {soil_temp}°C"
                )
        if ph is not None:
            if ph < ph_range[0] or ph > ph_range[1]:
                messages.append(
                    f"Ideal pH for corn is {ph_range[0]}–{ph_range[1]}, but yours is {ph}"
                )
        if messages:
            return f"{user_crop.capitalize()} may not thrive because " + " and ".join(messages) + "."
    if crop_lower == "banana":
        conditions = ideal_conditions["banana"]
        messages = []
        if soil_temp is not None and abs(soil_temp - conditions["ideal_temp"]) > 3:
            messages.append(
                f"ideal soil temperature is {conditions['ideal_temp']}°C while your soil is {soil_temp}°C"
            )
        if ph is not None and abs(ph - conditions["ideal_ph"]) > 0.5:
            messages.append(
                f"ideal pH is {conditions['ideal_ph']} while your soil pH is {ph}"
            )
        if messages:
            return f"{user_crop.capitalize()} was not recommended because " + " and ".join(messages) + "."
    elif crop_lower == "potato":
        conditions = ideal_conditions["potato"]
        temp_range = conditions["temp_range"]
        ph_range = conditions["ph_range"]
        messages = []
        if soil_temp is not None:
            if soil_temp < temp_range[0] or soil_temp > temp_range[1]:
                messages.append(
                    f"ideal soil temperature range is {temp_range[0]}–{temp_range[1]}°C while your soil is {soil_temp}°C"
                )
        if ph is not None:
            if ph < ph_range[0] or ph > ph_range[1]:
                messages.append(
                    f"ideal pH range is {ph_range[0]}–{ph_range[1]} while your soil pH is {ph}"
                )
        if messages:
            return f"{user_crop.capitalize()} was not recommended because " + " and ".join(messages) + "."
    return ""

def get_yield_prediction(crop, data):
    min_temp = crop.attributes.get("min_temp", 10)
    max_temp = crop.attributes.get("max_temp", 35)
    predicted_yield = (max_temp - min_temp) * 10  # Placeholder formula
    explanation = "Yield prediction is based on optimal temperature range."
    soil_temp = data.get("predicted_soil_temp", 20)
    if soil_temp < min_temp:
        explanation += f" However, your soil temp ({soil_temp}°C) is below the ideal {min_temp}°C, so yield may be reduced."
    elif soil_temp > max_temp:
        explanation += f" However, your soil temp ({soil_temp}°C) is above the ideal {max_temp}°C, so heat stress may reduce yield."
    return {"predicted_yield": predicted_yield, "explanation": explanation}

def get_crop_growth_risks(crop, data):
    ph = data.get("ph_level", 6.5)
    min_pH = crop.attributes.get("min_pH", 5.5)
    max_pH = crop.attributes.get("max_pH", 7.5)
    if ph < min_pH or ph > max_pH:
        return "Soil pH is not optimal for this crop."
    return "No significant risks."
