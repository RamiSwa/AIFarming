# recommendations/views.py
from django.contrib.auth.decorators import login_required
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from django.shortcuts import render
from .models import Recommendation, Crop
from .utils import load_model, load_pipeline, preprocess_input_data, make_predictions, fetch_and_merge_data, get_model_version  
from .serializers import RecommendationSerializer, RecommendationExportSerializer, CropSerializer
import pandas as pd
import numpy as np
from weather.models import WeatherData
from soil.models import SoilData
import logging
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from dateutil import parser as date_parser
from django.utils.timezone import make_aware
import pytz  # Required for setting timezone
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from celery.result import AsyncResult
from rest_framework.generics import ListAPIView
import csv
from django.http import HttpResponse
from django.db.models import Avg, Count
import random
from collections import defaultdict
from django.db.models.functions import TruncDate



import json

ai_model_version = json.dumps({
    "linear_regression": get_model_version("linear_regression"),
    "decision_tree": get_model_version("decision_tree"),
    "feature_engineering_pipeline": get_model_version("feature_engineering_pipeline")
})  


def fetch_latest_weather(lat, lon):
    """Fetches weather data with caching to reduce API calls."""
    
    # ✅ Step 1: Check if we have recent weather data (≤1 hour old)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    cached_weather = WeatherData.objects.filter(
        latitude=lat, longitude=lon, time__gte=one_hour_ago
    ).order_by("-time").first()

    if cached_weather:
        logging.info(f"✅ Using Cached Weather Data for ({lat}, {lon}) from {cached_weather.time}")
        return {
            "temperature_2m": cached_weather.temperature_2m,
            "relative_humidity_2m": cached_weather.relative_humidity_2m,
            "wind_speed_10m": cached_weather.wind_speed_10m,
            "precip_30day_sum": cached_weather.precipitation
        }

    # ✅ Step 2: If no cached data, fetch from Open-Meteo API
    logging.info(f"🔄 Fetching New Weather Data for ({lat}, {lon})")

    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    weather_response = requests.get(weather_url)

    if weather_response.status_code != 200:
        logging.error(f"⛔ Weather API failed for ({lat}, {lon})")
        return None  # Fail gracefully

    weather_data = weather_response.json().get("current_weather", {})

    # ✅ Fetch Historical Precipitation (Last 30 Days)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    precip_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={today}"
        f"&daily=precipitation_sum&timezone=UTC"
    )
    
    precip_response = requests.get(precip_url)

    if precip_response.status_code != 200:
        precip_30day_sum = 0  # Default if API fails
        avg_temp = weather_data.get("temperature", 15)  # Default 15°C if missing
    else:
        precip_data = precip_response.json().get("daily", {}).get("precipitation_sum", [])
        temp_max = precip_response.json().get("daily", {}).get("temperature_2m_max", [])
        temp_min = precip_response.json().get("daily", {}).get("temperature_2m_min", [])

        precip_30day_sum = sum(precip_data) if precip_data else 0
        avg_temp = (sum(temp_max) + sum(temp_min)) / (2 * len(temp_max)) if temp_max else weather_data.get("temperature", 15)

    # ✅ Save fetched weather into DB for future caching
    weather_instance = WeatherData.objects.create(
        time=timezone.now(),
        original_location="Live Data",
        temperature_2m=avg_temp,
        relative_humidity_2m=weather_data.get("relative_humidity", 50),  # Default 50% if missing
        wind_speed_10m=weather_data.get("windspeed"),
        precipitation=precip_30day_sum,
        latitude=lat,
        longitude=lon
    )

    logging.info(f"✅ Cached New Weather Data for ({lat}, {lon}) at {weather_instance.time}")

    return {
        "temperature_2m": avg_temp,
        "relative_humidity_2m": weather_instance.relative_humidity_2m,
        "wind_speed_10m": weather_instance.wind_speed_10m,
        "precip_30day_sum": weather_instance.precipitation
    }





# Configure logging for CSV errors
logging.basicConfig(
    filename="csv_upload_errors.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load models and pipeline
pipeline = load_pipeline("feature_engineering_pipeline.pkl")
models = {
    "linear_regression": load_model("linear_regression_model.pkl"),
    "decision_tree": load_model("decision_tree_model.pkl")
}



class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10  # Default: 10 recommendations per page
    page_size_query_param = 'page_size'  # Allow users to change page size
    max_page_size = 100  # Max: 100 recommendations per page



@login_required
def recommendations_page(request):
    return render(request, "recommendations/recommendations.html")

# ✅ View to Fetch AI Results
def fetch_results(request):
    return render(request, "recommendations/fetch_results.html")

# ✅ View to Manage Recommendations
def manage_recommendations(request):
    return render(request, "recommendations/manage_recommendations.html")

# ✅ View for CSV Upload & Task Monitoring
def csv_upload(request):
    return render(request, "recommendations/csv_upload.html")



class RecommendationPredictAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # 🔹 Get Crop from Request
            user_crop_name = request.data.get("crop", "").strip()
            if not user_crop_name:
                return Response({"status": "error", "message": "Crop name is required."}, status=400)

            try:
                crop = Crop.objects.get(name__iexact=user_crop_name)
            except Crop.DoesNotExist:
                return Response({"status": "error", "message": f"Crop '{user_crop_name}' not found."}, status=400)

            # 🔹 Fetch Latest Soil Data (to get coordinates)
            latest_soil = SoilData.objects.filter(
                soil_temp_0_to_7cm__gte=crop.min_soil_temp,
            ).order_by("-time").first()

            # 🚀 Handle Missing SoilData
            if not latest_soil:
                logging.warning("⛔ No SoilData found, estimating soil temperature based on weather.")
                lat = request.data.get("latitude")
                lon = request.data.get("longitude")

                if not lat or not lon:
                    latest_weather_data = WeatherData.objects.order_by("-time").first()
                    if latest_weather_data:
                        lat, lon = latest_weather_data.latitude, latest_weather_data.longitude
                    else:
                        return Response({"status": "error", "message": "No SoilData or WeatherData available. Latitude and Longitude are required."}, status=400)

                latest_weather = fetch_latest_weather(lat=lat, lon=lon)
                if not latest_weather:
                    return Response({"status": "error", "message": "Could not fetch live weather data."}, status=400)

                air_temp = latest_weather["temperature_2m"]
                estimated_soil_temp = max(0, air_temp - 3)
                latest_soil = SoilData.objects.create(
                    time=timezone.now(),
                    original_location="Estimated from Weather",
                    soil_temp_0_to_7cm=estimated_soil_temp,
                    location="Estimated Location",
                    latitude=lat,
                    longitude=lon,
                    data_source="estimated"
                )

            lat, lon = latest_soil.latitude, latest_soil.longitude
            latest_weather = fetch_latest_weather(lat=lat, lon=lon)
            if not latest_weather:
                return Response({"status": "error", "message": "Could not fetch live weather data."}, status=400)

            weather_instance = WeatherData.objects.create(
                time=timezone.now(),
                original_location="Live Data",
                temperature_2m=latest_weather["temperature_2m"],
                relative_humidity_2m=latest_weather["relative_humidity_2m"],
                wind_speed_10m=latest_weather["wind_speed_10m"],
                precipitation=latest_weather["precip_30day_sum"],
                latitude=lat,
                longitude=lon
            )

            input_data = pd.DataFrame([{
                "temperature_2m": latest_weather["temperature_2m"],
                "relative_humidity_2m": latest_weather["relative_humidity_2m"],
                "wind_speed_10m": latest_weather["wind_speed_10m"],
                "precip_30day_sum": latest_weather["precip_30day_sum"]
            }])

            predictions = make_predictions(models, input_data)
            predicted_soil_temp = float(predictions["linear_regression"][0])
            raw_yield_prediction = float(predictions["decision_tree"][0]) 
            base_yield = getattr(crop, "expected_yield", 10.0)

            temp_deviation = max(0, crop.min_soil_temp - predicted_soil_temp, predicted_soil_temp - crop.max_temp)
            yield_explanation = []

            if temp_deviation >= 3.5:
                risk_assessment = "High risk"
                expected_yield = base_yield * 0.4
                yield_explanation.append(f"⚠ AI predicted yield was {raw_yield_prediction:.2f}, but high-risk conditions reduced it to {expected_yield:.2f}.")
            elif temp_deviation >= 1.5:
                risk_assessment = "Medium risk"
                expected_yield = base_yield * 0.7
                yield_explanation.append(f"⚠ AI predicted yield was {raw_yield_prediction:.2f}, but medium-risk conditions adjusted it to {expected_yield:.2f}.")
            else:
                risk_assessment = "Low risk"
                expected_yield = base_yield * (1 + (predicted_soil_temp - crop.min_soil_temp) / (crop.max_temp - crop.min_soil_temp))
                yield_explanation.append(f"✅ AI predicted yield of {raw_yield_prediction:.2f} is optimal for current conditions.")
                

            if latest_weather["precip_30day_sum"] < 10:
                yield_explanation.append("⚠ Low precipitation detected, possible water stress.")
            elif latest_weather["precip_30day_sum"] > crop.max_precipitation:
                yield_explanation.append("⚠ High precipitation detected, risk of overwatering or flooding.")
            if latest_weather["wind_speed_10m"] > 15:
                yield_explanation.append("⚠ Strong winds detected, possible crop damage risk.")

            
            # 🛠 Mitigation Advice
            mitigation_suggestions = []
            if risk_assessment == "High risk":
                mitigation_suggestions.append("Solution: Delay planting by 10 days to avoid extreme temperatures.")
                mitigation_suggestions.append("Solution: Implement drainage solutions to reduce excess water in the field.")
            elif risk_assessment == "Medium risk":
                mitigation_suggestions.append("Solution: Consider increasing irrigation to counter water stress.")

            # 📊 Fetch Past Trends (e.g., Last Year's Temperature)
            one_year_ago = timezone.now() - timedelta(days=365)
            historical_weather = WeatherData.objects.filter(latitude=lat, longitude=lon, time__date=one_year_ago.date()).first()

            historical_trends = [f"Last year's temperature for this period was {historical_weather.temperature_2m}°C, current temperature is {predicted_soil_temp:.1f}°C."] if historical_weather else ["No historical data available."]


            # 📧 Generate Alert Messages
            alerts = ["📧 ALERT: Soil temperature too low. Expected yield reduced by 40%."] if risk_assessment == "High risk" else []


            # ✅ Confidence Score
            confidence_score = {
                "soil_temperature": float(np.around(predictions["linear_regression"][0], 2)),
                "yield_prediction": float(np.around(predictions["decision_tree"][0], 2))
            }

            
            # 🔹 Weather Summary
            weather_summary = f"{'Warm' if predicted_soil_temp > 15 else 'Cool'} with {'high' if latest_weather['precip_30day_sum'] > 20 else 'low'} precipitation."

            
            # 🔹 Next Best Action
            next_best_action = "Consider switching to Wheat due to better soil compatibility and lower risk of overwatering."
            
            # 🔹 Alternative Farming Advice
            alternative_farming_advice = ["Apply organic mulch to improve soil water retention.", "Monitor soil pH to optimize nutrient uptake for Corn."]
            

            recommended_crops = {"crops": []}
            TOLERANCE = 4
            for c in Crop.objects.all():
                is_within_range = (c.min_soil_temp - TOLERANCE) <= predicted_soil_temp <= (c.max_temp + TOLERANCE)
                if is_within_range:
                    recommended_crops["crops"].append(c.name)

            if not recommended_crops["crops"]:
                return Response({
                    "status": "error",
                    "message": "No suitable crops found for the current soil temperature.",
                    "predicted_soil_temp": predicted_soil_temp
                }, status=400)

            if risk_assessment == "High risk":
                optimal_planting_time = "Late Season" if predicted_soil_temp < crop.min_soil_temp else "Mid Season"
            else:
                optimal_planting_time = "Early Season"

            recommendation_instance = Recommendation.objects.create(
                user=request.user,
                soil_data=latest_soil,
                weather_data=weather_instance,
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

            return Response({
                "status": "success",
                "predicted_soil_temp": predicted_soil_temp,
                "predicted_yield": expected_yield,
                "risk_assessment": risk_assessment,
                "confidence_score": confidence_score,
                "weather_summary": weather_summary,
                "yield_explanation": yield_explanation,
                "mitigation_suggestions": mitigation_suggestions,
                "historical_trends": historical_trends,
                "alerts": alerts,
                "next_best_action": next_best_action,
                "alternative_farming_advice": alternative_farming_advice,
                "recommendation": {
                    "id": recommendation_instance.id,
                    "crop": crop.name,
                    "recommended_crops": recommended_crops,
                    "expected_yield": expected_yield,
                    "risk_assessment": risk_assessment,
                    "optimal_planting_time": optimal_planting_time,
                    "ai_model_version": ai_model_version
                }
            }, status=200)
        
        except Exception as e:
            logging.error(f"Error in RecommendationPredictAPIView: {str(e)}")
            return Response({"status": "error", "message": str(e)}, status=400)




class RecommendationListCreateAPIView(ListAPIView):
    serializer_class = RecommendationSerializer
    pagination_class = StandardResultsSetPagination  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Recommendation.objects.filter(user=self.request.user)
        crop = self.request.query_params.get('crop')
        risk = self.request.query_params.get('risk')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if crop:
            qs = qs.filter(crop__name__iexact=crop)  # adjust lookup if needed
        if risk:
            qs = qs.filter(risk_assessment__iexact=risk)
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)

        return qs.order_by('-created_at')


class RecommendationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            recommendation = Recommendation.objects.get(pk=pk, user=request.user)
            serializer = RecommendationSerializer(recommendation)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Recommendation.DoesNotExist:
            return Response({"status": "error", "message": "Recommendation not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            recommendation = Recommendation.objects.get(pk=pk, user=request.user)
            recommendation.delete()
            return Response({"status": "success", "message": "Recommendation deleted."}, status=status.HTTP_200_OK)
        except Recommendation.DoesNotExist:
            return Response({"status": "error", "message": "Recommendation not found."}, status=status.HTTP_404_NOT_FOUND)




# CSV Export Endpoint
class RecommendationExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        qs = Recommendation.objects.filter(user=request.user)
        crop = request.query_params.get('crop')
        risk = request.query_params.get('risk')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if crop:
            qs = qs.filter(crop__name__iexact=crop)
        if risk:
            qs = qs.filter(risk_assessment__iexact=risk)
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        return qs.order_by('-created_at')

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset(request)
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="recommendations_export.csv"'
        writer = csv.writer(response)

        # Write header row
        writer.writerow([
            "User", "Crop", "Expected Yield", "Predicted Yield", "Predicted Soil Temp",
            "Risk Assessment", "Optimal Planting Time",
            "Weather Summary", "Next Best Action", "AI Model Version", "Created At"
        ])

        for rec in qs:
            user_email = rec.user.email if rec.user else ""
            crop_name = rec.crop.name if rec.crop else "N/A"
            expected_yield = rec.expected_yield
            predicted_yield = rec.predicted_yield
            predicted_soil_temp = rec.predicted_soil_temp
            risk_assessment = rec.risk_assessment
            optimal_planting_time = rec.optimal_planting_time
            weather_summary = rec.weather_summary
            next_best_action = rec.next_best_action

            # Format AI model version (similar to your Admin code)
            try:
                versions = json.loads(rec.ai_model_version)
                formatted_ai_model_version = " | ".join(
                    f"{key.replace('_', ' ').title()}: {value}" for key, value in versions.items()
                )
            except (json.JSONDecodeError, TypeError):
                formatted_ai_model_version = rec.ai_model_version

            created_at = rec.created_at.strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([
                user_email, crop_name, expected_yield, predicted_yield, predicted_soil_temp,
                risk_assessment, optimal_planting_time,
                weather_summary, next_best_action, formatted_ai_model_version, created_at
            ])

        return response


# CSV Export Preview Endpoint (returns JSON preview data, e.g., first 10 records)
class RecommendationExportPreviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        qs = Recommendation.objects.filter(user=request.user)
        crop = request.query_params.get('crop')
        risk = request.query_params.get('risk')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if crop:
            qs = qs.filter(crop__name__iexact=crop)
        if risk:
            qs = qs.filter(risk_assessment__iexact=risk)
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        return qs.order_by('-created_at')

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset(request)
        preview_qs = qs[:10]  # Limit preview to 10 records
        serializer = RecommendationExportSerializer(preview_qs, many=True)
        return Response(serializer.data, status=200)




logging.basicConfig(filename="csv_upload_errors.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")



import os
import logging
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from recommendations.tasks import process_csv_upload

class FileUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided. Please upload a valid CSV file."}, status=400)

        # ✅ Save File to Shared `/app/media/uploads/`
        upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(upload_dir, exist_ok=True)  # ✅ Ensure directory exists

        file_path = os.path.join(upload_dir, file_obj.name)
        with open(file_path, "wb+") as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        logging.info(f"✅ File {file_obj.name} saved at {file_path}")

        # ✅ Trigger Async Celery Task
        task = process_csv_upload.delay(file_path, request.user.id)

        return Response({
            "message": "CSV processing started asynchronously.",
            "task_id": task.id
        }, status=202)






class TaskStatusAPIView(APIView):
    def get(self, request, task_id, *args, **kwargs):
        """Check the status of a Celery task using the task ID."""
        task = AsyncResult(task_id)  # Fetch task status from Celery
        response_data = {
            "task_id": task_id,
            "status": task.status,  # Possible values: PENDING, SUCCESS, FAILURE
            "result": task.result if task.successful() else None,  # Only show result if successful
        }
        return Response(response_data)






class RecommendationSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Recommendation.objects.filter(user=request.user)
        total = qs.count()
        avg_yield = qs.aggregate(avg_yield=Avg('predicted_yield'))['avg_yield']
        low_risk = qs.filter(risk_assessment="Low risk").count()
        medium_risk = qs.filter(risk_assessment="Medium risk").count()
        high_risk = qs.filter(risk_assessment="High risk").count()
        latest_rec = qs.order_by('-created_at').first()
        latest_date = latest_rec.created_at.strftime('%Y-%m-%d') if latest_rec else "--"

        # Compute percentages
        low_pct = (low_risk / total * 100) if total > 0 else 0
        med_pct = (medium_risk / total * 100) if total > 0 else 0
        high_pct = (high_risk / total * 100) if total > 0 else 0

        return Response({
            "total": total,
            "predicted_yield_avg": round(avg_yield, 2) if avg_yield is not None else "--",
            "low_risk": low_risk,
            "medium_risk": medium_risk,
            "high_risk": high_risk,
            "latest_date": latest_date,
            "low_pct": round(low_pct, 1),
            "medium_pct": round(med_pct, 1),
            "high_pct": round(high_pct, 1)
        })




class SampleRecommendationsCSVDownloadAPIView(APIView):
    def get(self, request):
        """
        Generate and return a sample CSV file for recommendations with all required fields.
        """
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="sample_recommendations.csv"'

        writer = csv.writer(response)

        # Write CSV header
        writer.writerow([
            "time", "crop", "temperature_2m", "relative_humidity_2m",
            "wind_speed_10m", "precip_30day_sum", "latitude", "longitude"
        ])

        # Write sample data rows
        writer.writerow([
            "2025-02-16", "Barley", "13.5", "60", "5.2", "20.5", "34.0522", "-118.2437"
        ])
        writer.writerow([
            "2025-02-16", "Corn", "15.0", "55", "6.8", "18.9", "36.7783", "-119.4179"
        ])

        return response
    


class CropListAPIView(ListAPIView):
    queryset = Crop.objects.all().order_by("name")  # Sort alphabetically
    serializer_class = CropSerializer
    permission_classes = [IsAuthenticated]


    def get(self, request, *args, **kwargs):
        crops = Crop.objects.values_list("name", flat=True)  # Get crop names
        crop_colors = self.generate_crop_colors(crops)
        return Response({"crops": list(crops), "colors": crop_colors})

    def generate_crop_colors(self, crops):
        """Assigns a unique color to each crop dynamically"""
        random.seed(42)  # Ensures consistent colors across requests
        return {crop: f"rgb({random.randint(50, 200)}, {random.randint(50, 200)}, {random.randint(50, 200)})" for crop in crops}

    
    
# ============================================================
# NEW API ENDPOINTS for Chart Data Aggregation
# ============================================================

class TemperatureTrendsChartDataAPIView(APIView):
    """
    Aggregates soil temperature trends over time grouped by crop.
    Returns data in the format:
    {
      "labels": [ "2025-02-15", "2025-02-16", ... ],
      "datasets": [
         {
            "crop": "Wheat",
            "optimal_min": 12,
            "optimal_max": 18,
            "data": [14.2, null, 15.0, ...]
         },
         ...
      ]
    }
    Query params (optional): crop, risk, start_date, end_date
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Recommendation.objects.filter(user=request.user)
        # Optional filtering similar to your list view
        crop = request.query_params.get('crop')
        risk = request.query_params.get('risk')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if crop:
            qs = qs.filter(crop__name__iexact=crop)
        if risk:
            qs = qs.filter(risk_assessment__iexact=risk)
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        
        # Group by crop and by day (using TruncDate on created_at)
        qs = qs.annotate(date=TruncDate('created_at')).values('crop__name', 'date') \
               .annotate(avg_soil_temp=Avg('predicted_soil_temp')) \
               .order_by('date')
        
        # Organize data by crop
        data_by_crop = defaultdict(dict)
        all_dates = set()
        for entry in qs:
            crop_name = entry['crop__name']
            date_str = entry['date'].strftime("%Y-%m-%d")
            all_dates.add(date_str)
            data_by_crop[crop_name][date_str] = round(entry['avg_soil_temp'], 2) if entry['avg_soil_temp'] is not None else None

        sorted_dates = sorted(list(all_dates))
        datasets = []
        for crop_name, temp_data in data_by_crop.items():
            # Fetch optimal values from Crop model
            try:
                crop_obj = Crop.objects.get(name__iexact=crop_name)
                optimal_min = crop_obj.min_soil_temp
                optimal_max = crop_obj.max_temp  # or whichever field holds the optimal high temperature
            except Crop.DoesNotExist:
                optimal_min, optimal_max = None, None
            # Build the data array for each date (fill missing with None)
            data_array = [temp_data.get(date, None) for date in sorted_dates]
            datasets.append({
                "crop": crop_name,
                "optimal_min": optimal_min,
                "optimal_max": optimal_max,
                "data": data_array,
            })

        return Response({
            "labels": sorted_dates,
            "datasets": datasets
        })


class PredictedYieldChartDataAPIView(APIView):
    """
    Aggregates average predicted vs. expected yield for each crop.
    Returns data in the format:
    {
      "data": [
         {
            "crop": "Wheat",
            "avg_predicted_yield": 20.5,
            "avg_expected_yield": 25.0,
            "risk_counts": {"Low risk": 5, "Medium risk": 2, "High risk": 1}
         },
         ...
      ]
    }
    Query params (optional): crop, risk, start_date, end_date
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Recommendation.objects.filter(user=request.user)
        crop = request.query_params.get('crop')
        risk = request.query_params.get('risk')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if crop:
            qs = qs.filter(crop__name__iexact=crop)
        if risk:
            qs = qs.filter(risk_assessment__iexact=risk)
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        
        qs_grouped = qs.values('crop__name').annotate(
            avg_predicted_yield=Avg('predicted_yield'),
            avg_expected_yield=Avg('expected_yield'),
            count=Count('id')
        )

        # Also count risk levels per crop
        data = []
        for group in qs_grouped:
            crop_name = group['crop__name']
            sub_qs = qs.filter(crop__name__iexact=crop_name)
            risk_counts = {
                "Low risk": sub_qs.filter(risk_assessment="Low risk").count(),
                "Medium risk": sub_qs.filter(risk_assessment="Medium risk").count(),
                "High risk": sub_qs.filter(risk_assessment="High risk").count()
            }
            data.append({
                "crop": crop_name,
                "avg_predicted_yield": round(group['avg_predicted_yield'], 2) if group['avg_predicted_yield'] is not None else None,
                "avg_expected_yield": round(group['avg_expected_yield'], 2) if group['avg_expected_yield'] is not None else None,
                "risk_counts": risk_counts
            })
        return Response({"data": data})


class WeatherSuitabilityChartDataAPIView(APIView):
    """
    Returns a list of data points for a scatter plot.
    For each recommendation, we pull weather parameters from its weather_data
    and compute a numerical suitability score based on risk:
      - "Low risk": 100
      - "Medium risk": 70
      - "High risk": 40
    Each data point includes:
      - temperature, humidity, wind_speed, precipitation, suitability, crop, date
    Query params (optional): crop, risk, start_date, end_date
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Recommendation.objects.filter(user=request.user).select_related('weather_data', 'crop')
        crop = request.query_params.get('crop')
        risk = request.query_params.get('risk')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if crop:
            qs = qs.filter(crop__name__iexact=crop)
        if risk:
            qs = qs.filter(risk_assessment__iexact=risk)
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)

        risk_map = {"Low risk": 100, "Medium risk": 70, "High risk": 40}
        points = []
        for rec in qs:
            weather = rec.weather_data
            if not weather:
                continue
            points.append({
                "temperature": weather.temperature_2m,
                "humidity": weather.relative_humidity_2m,
                "wind_speed": weather.wind_speed_10m,
                "precipitation": weather.precipitation,
                "suitability": risk_map.get(rec.risk_assessment, 50),
                "crop": rec.crop.name if rec.crop else "Unknown",
                "date": rec.created_at.strftime("%Y-%m-%d")
            })
        return Response({"data": points})
