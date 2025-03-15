import os
import time
import logging
import pandas as pd
import numpy as np
from celery import shared_task
from django.utils.timezone import make_aware
from django.contrib.auth import get_user_model
from dateutil import parser as date_parser
from weather.models import WeatherData
from soil.models import SoilData
from recommendations.models import Recommendation, Crop
from recommendations.views import fetch_latest_weather
from .utils import load_model, load_pipeline, preprocess_input_data, make_predictions, fetch_and_merge_data
from django.utils import timezone
from datetime import timedelta
import pytz

# Load models and pipeline
pipeline = load_pipeline("feature_engineering_pipeline.pkl")
models = {
    "linear_regression": load_model("linear_regression_model.pkl"),
    "decision_tree": load_model("decision_tree_model.pkl")
}

User = get_user_model()

@shared_task
def process_csv_upload(file_path, user_id):
    try:
        # Ensure the file is fully written (max wait: 10s)
        for _ in range(10):
            if os.path.exists(file_path):
                break
            time.sleep(1)

        if not os.path.exists(file_path):
            logging.error(f"⛔ CSV file not found: {file_path}")
            return {"error": f"File {file_path} not found."}

        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()

        required_columns = {
            "time",
            "crop",
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "precip_30day_sum",
            "latitude",
            "longitude"
        }
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            logging.error(f"⛔ Missing required columns: {', '.join(missing_columns)}")
            return {"error": f"Missing required columns: {', '.join(missing_columns)}"}

        logging.info(f"✅ Processing CSV {file_path} with columns: {df.columns.tolist()}")

        user = User.objects.get(id=user_id)
        recommendations_created = []

        for index, row in df.iterrows():
            try:
                logging.debug(f"📌 Processing Row {index + 1}: {row.to_dict()}")

                # Convert `time` to a timezone-aware datetime object
                time_str = str(row["time"]).strip()
                naive_time = date_parser.parse(time_str)
                time_obj = make_aware(naive_time, pytz.UTC)

                latitude, longitude = float(row["latitude"]), float(row["longitude"])
                logging.info(f"📌 Processing Row {index + 1} ➡ Parsed Time: {time_obj}, Lat: {latitude}, Lon: {longitude}")

                # Fetch WeatherData & SoilData
                weather_data = WeatherData.objects.filter(
                    latitude=latitude, longitude=longitude, time__lte=time_obj
                ).order_by("-time").first()
                soil_data = SoilData.objects.filter(
                    latitude=latitude, longitude=longitude, time__lte=time_obj
                ).order_by("-time").first()

                if not weather_data:
                    logging.warning(f"⛔ No WeatherData found for Row {index + 1}, fetching live data...")
                    live_weather = fetch_latest_weather(lat=latitude, lon=longitude)
                    if live_weather:
                        weather_data = WeatherData.objects.create(
                            time=timezone.now(),
                            original_location="Live Data",
                            temperature_2m=live_weather["temperature_2m"],
                            relative_humidity_2m=live_weather["relative_humidity_2m"],
                            wind_speed_10m=live_weather["wind_speed_10m"],
                            precipitation=live_weather["precip_30day_sum"],
                            latitude=latitude,
                            longitude=longitude
                        )
                    else:
                        logging.error(f"⛔ Failed to fetch live weather for Row {index + 1}, skipping entry.")
                        continue

                if not soil_data:
                    estimated_soil_temp = max(0, weather_data.temperature_2m - 3)
                    soil_data = SoilData.objects.create(
                        time=timezone.now(),
                        original_location="Estimated from Weather",
                        soil_temp_0_to_7cm=estimated_soil_temp,
                        latitude=latitude,
                        longitude=longitude,
                        data_source="estimated"
                    )

                # Fetch Crop Details
                crop_name = row["crop"].strip()
                try:
                    crop = Crop.objects.get(name__iexact=crop_name)
                except Crop.DoesNotExist:
                    logging.error(f"⛔ ERROR: Crop '{crop_name}' not found for row {index + 1}, skipping entry.")
                    continue

                # AI Prediction using weather data as input
                input_data = pd.DataFrame([{
                    "temperature_2m": weather_data.temperature_2m,
                    "relative_humidity_2m": weather_data.relative_humidity_2m,
                    "wind_speed_10m": weather_data.wind_speed_10m,
                    "precip_30day_sum": weather_data.precipitation
                }])
                predictions = make_predictions(models, input_data)

                predicted_soil_temp = predictions.get("linear_regression", [None])[0]
                if predicted_soil_temp is None:
                    logging.error(f"⛔ ERROR: Soil temp prediction failed for row {index + 1}. Skipping entry.")
                    continue
                predicted_soil_temp = float(predicted_soil_temp)

                raw_yield_prediction = predictions.get("decision_tree", [None])[0]
                if raw_yield_prediction is None:
                    logging.error(f"⛔ ERROR: Yield prediction failed for row {index + 1}. Skipping entry.")
                    continue
                raw_yield_prediction = float(raw_yield_prediction)

                # Determine Risk Level & Expected Yield
                base_yield = getattr(crop, "expected_yield", 10.0)
                temp_deviation = max(0, crop.min_soil_temp - predicted_soil_temp, predicted_soil_temp - crop.max_temp)

                if temp_deviation >= 3.5:
                    risk_assessment = "High risk"
                    expected_yield = base_yield * 0.4
                elif temp_deviation >= 1.5:
                    risk_assessment = "Medium risk"
                    expected_yield = base_yield * 0.7
                else:
                    risk_assessment = "Low risk"
                    expected_yield = base_yield * (1 + (predicted_soil_temp - crop.min_soil_temp) / (crop.max_temp - crop.min_soil_temp))

                # Improved Crop Recommendations
                recommended_crops = {"crops": []}
                crop_scores = []

                # Adaptive tolerance based on soil temperature
                if predicted_soil_temp < 5:
                    TOLERANCE = 8
                elif predicted_soil_temp < 10:
                    TOLERANCE = 6
                elif predicted_soil_temp < 15:
                    TOLERANCE = 5
                else:
                    TOLERANCE = 4

                # Score crops based on suitability
                for c in Crop.objects.all():
                    is_within_range = (c.min_soil_temp - TOLERANCE) <= predicted_soil_temp <= (c.max_temp + TOLERANCE)
                    if is_within_range:
                        temp_distance = abs(predicted_soil_temp - ((c.min_soil_temp + c.max_temp) / 2))
                        precipitation_factor = c.max_precipitation
                        crop_scores.append((c.name, temp_distance, precipitation_factor))

                # Sort crops (60% temperature, 40% precipitation)
                crop_scores.sort(key=lambda x: (x[1] * 0.6, x[2] * 0.4))

                # Select top 4 recommended crops
                for crop_name_val, _, _ in crop_scores[:4]:
                    recommended_crops["crops"].append(crop_name_val)

                # Ensure at least 3 crops are recommended
                if len(recommended_crops["crops"]) < 3:
                    sorted_all_crops = sorted(
                        Crop.objects.all(),
                        key=lambda c: abs(predicted_soil_temp - ((c.min_soil_temp + c.max_temp) / 2))
                    )
                    extra_crops = [c.name for c in sorted_all_crops if c.name not in recommended_crops["crops"]]
                    while len(recommended_crops["crops"]) < 3 and extra_crops:
                        recommended_crops["crops"].append(extra_crops.pop(0))

                # Final crop list adjustments
                if risk_assessment == "High risk" and len(recommended_crops["crops"]) > 4:
                    recommended_crops["crops"] = recommended_crops["crops"][:4]

                # Optimal Planting Time Logic
                if risk_assessment == "High risk":
                    optimal_planting_time = "Late Season" if predicted_soil_temp < crop.min_soil_temp else "Mid Season"
                else:
                    optimal_planting_time = "Early Season"

                # Additional fields (mirroring RecommendationPredictAPIView)
                yield_explanation = []
                if risk_assessment == "High risk":
                    yield_explanation.append(f"⚠ AI predicted yield was {raw_yield_prediction:.2f}, but high-risk conditions reduced it to {expected_yield:.2f}.")
                elif risk_assessment == "Medium risk":
                    yield_explanation.append(f"⚠ AI predicted yield was {raw_yield_prediction:.2f}, but medium-risk conditions adjusted it to {expected_yield:.2f}.")
                else:
                    yield_explanation.append(f"✅ AI predicted yield of {raw_yield_prediction:.2f} is optimal for current conditions.")

                # Add weather-based messages
                if weather_data.precipitation < 10:
                    yield_explanation.append("⚠ Low precipitation detected, possible water stress.")
                elif weather_data.precipitation > crop.max_precipitation:
                    yield_explanation.append("⚠ High precipitation detected, risk of overwatering or flooding.")
                if weather_data.wind_speed_10m > 15:
                    yield_explanation.append("⚠ Strong winds detected, possible crop damage risk.")

                mitigation_suggestions = []
                if risk_assessment == "High risk":
                    mitigation_suggestions.append("Solution: Delay planting by 10 days to avoid extreme temperatures.")
                    mitigation_suggestions.append("Solution: Implement drainage solutions to reduce excess water in the field.")
                elif risk_assessment == "Medium risk":
                    mitigation_suggestions.append("Solution: Consider increasing irrigation to counter water stress.")

                one_year_ago = timezone.now() - timedelta(days=365)
                historical_weather = WeatherData.objects.filter(
                    latitude=latitude, longitude=longitude, time__date=one_year_ago.date()
                ).first()
                if historical_weather:
                    historical_trends = [
                        f"Last year's temperature for this period was {historical_weather.temperature_2m}°C, current temperature is {predicted_soil_temp:.1f}°C."
                    ]
                else:
                    historical_trends = ["No historical data available."]

                alerts = []
                if risk_assessment == "High risk":
                    alerts.append("📧 ALERT: Soil temperature too low. Expected yield reduced by 40%.")

                next_best_action = "Consider switching to Wheat due to better soil compatibility and lower risk of overwatering."
                alternative_farming_advice = [
                    "Apply organic mulch to improve soil water retention.",
                    "Monitor soil pH to optimize nutrient uptake for Corn."
                ]
                confidence_score = {
                    "soil_temperature": float(np.around(predicted_soil_temp, 2)),
                    "yield_prediction": float(np.around(raw_yield_prediction, 2))
                }
                weather_summary = f"{'Warm' if predicted_soil_temp > 15 else 'Cool'} with {'high' if weather_data.precipitation > 20 else 'low'} precipitation."
                ai_model_version = "CSV Import v1.1"

                # Save Recommendation in DB with all fields
                recommendation = Recommendation.objects.create(
                    user=user,
                    soil_data=soil_data,
                    weather_data=weather_data,
                    crop=crop,
                    recommended_crops=recommended_crops,
                    expected_yield=expected_yield,
                    risk_assessment=risk_assessment,
                    optimal_planting_time=optimal_planting_time,
                    predicted_yield=raw_yield_prediction,
                    predicted_soil_temp=predicted_soil_temp,
                    confidence_score=confidence_score,
                    weather_summary=weather_summary,
                    yield_explanation=yield_explanation,
                    mitigation_suggestions=mitigation_suggestions,
                    historical_trends=historical_trends,
                    alerts=alerts,
                    next_best_action=next_best_action,
                    alternative_farming_advice=alternative_farming_advice,
                    ai_model_version=ai_model_version
                )
                recommendations_created.append(recommendation.id)

            except Exception as e:
                logging.error(f"⛔ ERROR processing row {index + 1}: {str(e)}")
                continue

        return {"message": "CSV processed", "created_recommendations": recommendations_created}

    except Exception as e:
        return {"error": str(e)}
