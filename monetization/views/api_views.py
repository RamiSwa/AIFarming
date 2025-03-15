# monetization/views/api_views.py
import json
import logging
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from monetization.models import ReportRequest, AIReport, CropSuitability, Feedback
from monetization.services.pdf_generator import generate_pdf
from monetization.utils import (
    get_lat_long, get_soil_temp, get_weather_data,
    predict_soil_temperature, get_recommended_crops, get_suitable_crops,
    generate_risk_assessment, get_yield_prediction,
    get_crop_growth_risks, generate_mitigation_strategies,
    generate_ai_alerts, generate_next_best_action, evaluate_soil_risks,
    check_crop_feasibility, forecast_future_climate,
    calculate_crop_feasibility_score, generate_crop_rotation_plan
)
from django.shortcuts import render
from django.conf import settings
from django.urls import reverse
import logging
import os
from monetization.utils import has_active_subscription


# Setup logging for debugging
logger = logging.getLogger(__name__)





## AI REPORT PDF 
# --- Unit Conversion Helpers ---
def c_to_f(celsius):
    return round((celsius * 9/5) + 32, 2)

def mm_to_in(mm):
    return round(mm / 25.4, 2)

# --- Report Request API ---
class RequestReportView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data.copy()

        units = data.get("units", "metric")
        weather_provided = ("wind_speed_10m" in request.data and "precipitation" in request.data)

        # 1) Validate & Get Location
        if not data.get("latitude") or not data.get("longitude"):
            lat, lon = get_lat_long(data.get("location"))
            if lat and lon:
                data["latitude"], data["longitude"] = lat, lon
            else:
                return Response({"error": "Invalid location"}, status=status.HTTP_400_BAD_REQUEST)

        # 2) Measured Soil Temp if missing
        if not data.get("soil_temp_0_to_7cm"):
            measured_soil_temp = get_soil_temp(data["latitude"], data["longitude"]) or 20
            data["measured_soil_temp"] = measured_soil_temp
        else:
            data["measured_soil_temp"] = data["soil_temp_0_to_7cm"]

        # 3) Fetch Weather Data
        weather_data = get_weather_data(data["latitude"], data["longitude"])
        if not weather_data:
            return Response({"error": "Failed to retrieve weather data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data["weather_source"] = "real-time" if weather_provided else "historical trends"

        if units == "imperial":
            data["temperature_2m"] = c_to_f(weather_data.get("temperature_2m", 20))
            data["wind_speed_10m"] = round(weather_data.get("wind_speed_10m", 5) * 2.23694, 2)
            data["precipitation"] = mm_to_in(weather_data.get("precipitation", 0))
        else:
            data["temperature_2m"] = weather_data.get("temperature_2m", 20)
            data["wind_speed_10m"] = weather_data.get("wind_speed_10m", 5)
            data["precipitation"] = weather_data.get("precipitation", 0)

        data["relative_humidity_2m"] = weather_data.get("relative_humidity_2m", 50)

        # 4) Create a ReportRequest once using filtered data
        allowed_fields = {field.name for field in ReportRequest._meta.fields}
        filtered_data = {key: value for key, value in data.items() if key in allowed_fields}
        report_request = ReportRequest.objects.create(user=user, **filtered_data)
        
        # 5) AI Soil Temp Prediction
        predictions = predict_soil_temperature(data)
        final_predicted_temp = round(predictions["decision_tree"], 2)
        data["predicted_soil_temp"] = final_predicted_temp

        # 6) AI Crop Recommendations
        soil_type = data.get("soil_type", "")
        if not soil_type:
            data["soil_type"] = "missing"
        else:
            data["soil_type"] = soil_type.lower()

        recommended_crops = get_recommended_crops(
            soil_temp=final_predicted_temp,
            ph_level=data.get("ph_level", 6.5),
            precipitation=data.get("precipitation", 30),
            soil_type=data["soil_type"]
        )

        # Future climate predictions
        climate_forecast = forecast_future_climate(final_predicted_temp)

        # 7) Build Crop Details
        crop_details = []
        for crop_name in recommended_crops:
            crop = CropSuitability.objects.filter(name=crop_name).first()
            if crop:
                yield_info = get_yield_prediction(crop, data)
                if crop.preferred_growing_season:
                    if isinstance(crop.preferred_growing_season, str):
                        try:
                            season_list = json.loads(crop.preferred_growing_season)
                        except Exception:
                            season_list = []
                    else:
                        season_list = crop.preferred_growing_season
                    if season_list:
                        season_value = min([int(s) for s in season_list])
                        if season_value <= 4:
                            best_planting_time = "Spring & Fall 🌱"
                        elif season_value <= 8:
                            best_planting_time = "Summer 🌾"
                        else:
                            best_planting_time = "Winter 🍂"
                    else:
                        best_planting_time = "Not Available"
                else:
                    best_planting_time = "Not Available"

                pH = data.get("ph_level", 6.5)
                min_pH = crop.attributes.get("min_pH", 5.5)
                max_pH = crop.attributes.get("max_pH", 7.5)
                min_temp = crop.attributes.get("min_temp", 10)
                max_temp = crop.attributes.get("max_temp", 35)

                pH_in_range = (pH >= min_pH and pH <= max_pH)
                temp_in_range = (final_predicted_temp >= min_temp and final_predicted_temp <= max_temp)

                if pH_in_range and temp_in_range:
                    short_explanation = (
                        f"{crop.name} is recommended because your pH ({pH}) is within {min_pH}–{max_pH}, "
                        f"and soil temp ({final_predicted_temp}°C) is within {min_temp}–{max_temp}°C."
                    )
                    if abs(pH - max_pH) < 0.001:
                        short_explanation += " (Keep an eye if pH goes above 7.5!)"
                elif not pH_in_range and not temp_in_range:
                    short_explanation = (
                        f"{crop.name} is not optimal because your pH ({pH}) is outside {min_pH}–{max_pH}, "
                        f"and soil temp ({final_predicted_temp}°C) is outside {min_temp}–{max_temp}°C."
                    )
                elif not pH_in_range:
                    short_explanation = (
                        f"{crop.name} is not optimal because your pH ({pH}) is outside {min_pH}–{max_pH}."
                    )
                else:
                    short_explanation = (
                        f"{crop.name} is not optimal because your soil temp ({final_predicted_temp}°C) "
                        f"is outside {min_temp}–{max_temp}°C."
                    )

                growth_risks = get_crop_growth_risks(crop, data)
                feasibility_score = calculate_crop_feasibility_score(crop, data)

                crop_info = {
                    "name": f"{crop.name} ✅" if (pH_in_range and temp_in_range) else f"{crop.name}",
                    "crop_type": crop.crop_type,
                    "min_temp": min_temp,
                    "max_temp": max_temp,
                    "temperature_suitability": f"{min_temp}°C - {max_temp}°C",
                    "min_pH": min_pH,
                    "max_pH": max_pH,
                    "suitable_soil_types": crop.suitable_soil_types,
                    "preferred_growing_season": crop.preferred_growing_season,
                    "predicted_yield": yield_info["predicted_yield"],
                    "yield_explanation": yield_info["explanation"] + f" {short_explanation}",
                    "growth_risks": growth_risks,
                    "confidence": "High (90%)",
                    "best_planting_time": best_planting_time,
                    "feasibility_score": feasibility_score
                }
                crop_details.append(crop_info)

        fully_in_range_crops = []
        for cd in crop_details:
            if cd["name"].endswith("✅"):
                fully_in_range_crops.append(cd["name"].replace(" ✅", ""))

        # 8) Risk Assessment & Mitigation
        risk_assessment = generate_risk_assessment(data)
        mitigation_strategies = generate_mitigation_strategies(data)

        ai_alerts = []
        precipitation_val = data.get("precipitation", 0)
        if units == "imperial":
            if precipitation_val > 4:
                ai_alerts.append("🔴 Weather Risk: High precipitation (inches) - Overwatering risk.")
        else:
            if precipitation_val > 100:
                ai_alerts.append("🔴 Weather Risk: High precipitation detected - Overwatering risk.")

        wind_val = data.get("wind_speed_10m", 5)
        if units == "imperial":
            if wind_val > 22:
                ai_alerts.append("🌦 Weather Risk: Strong winds detected - Consider windbreaks.")
        else:
            if wind_val > 10:
                ai_alerts.append("🌦 Weather Risk: Strong winds detected - Consider windbreaks.")

        temp_val = data.get("temperature_2m", 20)
        if units == "imperial":
            if temp_val < 50 or temp_val > 95:
                ai_alerts.append("🌦 Weather Risk: Temperature fluctuation risk - Adjust irrigation.")
        else:
            if temp_val < 10 or temp_val > 35:
                ai_alerts.append("🌦 Weather Risk: Temperature fluctuation risk - Adjust irrigation.")

        ph_val = data.get("ph_level", 6.5)
        if ph_val > 7.5:
            ai_alerts.append("🌱 Soil Issue: Soil too alkaline – Consider adding organic matter or sulfur.")

        nitrogen_val = data.get("nitrogen")
        if nitrogen_val and nitrogen_val < 30:
            ai_alerts.append(
                f"🌱 Soil Issue: Your soil nitrogen ({nitrogen_val} mg/kg) is below the optimal 20 mg/kg. "
                "Apply 40 kg/ha of Urea."
            )

        for crop in crop_details:
            if crop.get("growth_risks") and "No significant risks" not in crop.get("growth_risks"):
                ai_alerts.append(f"🌾 Crop-Specific Risk: {crop.get('name')} - {crop.get('growth_risks')}")

        if not ai_alerts:
            ai_alerts = ["No significant alerts."]

        # 9) Next Best Action
        user_crop_pref = data.get("crop_type", "N/A")
        next_best_action = "🌱 Next Best Action\n"
        if fully_in_range_crops:
            next_best_action += f"✅ Primary Recommended Crop: {fully_in_range_crops[0]}\n"
            if len(fully_in_range_crops) > 1:
                next_best_action += f"🔹 Alternative Crop: {fully_in_range_crops[1]}\n"
        elif recommended_crops:
            next_best_action += (
                "All recommended crops require some soil adjustments (pH or temperature) "
                "to be fully optimal. Consider pH correction or other mitigation.\n"
            )
        else:
            next_best_action += "No recommended crops found.\n"

        feasibility_msg = check_crop_feasibility(user_crop_pref, data)
        if feasibility_msg:
            next_best_action += f"🔹 {feasibility_msg}\n"
        else:
            next_best_action += (
                f"🔹 You mentioned a preference for '{user_crop_pref}'. "
                "If conditions remain stable, you might still plant it, "
                "but be aware of yield/risk trade-offs.\n"
            )

        if user_crop_pref.lower() == "corn" and climate_forecast["60_days"] < 10:
            next_best_action += (
                f"🔹 Note: Corn is a warm-season crop. Our 60-day forecast is {climate_forecast['60_days']}°C, "
                "which may be too cold. You might wait until ~90 days when temp is higher.\n"
            )

        next_best_action += "🔹 Companion Crops: Consider planting legumes for better nitrogen retention.\n"

        # 10) Additional Data
        historical_weather = {
            "avg_max_temp": 29,
            "avg_min_temp": 14,
            "total_precip": 650,
            "avg_wind_speed": 6,
            "start_date": "2020-01-01",
            "end_date": "2025-01-01"
        }
        regional_avg_yield = {"regional_avg": 13.0}
        rotation_plan = generate_crop_rotation_plan(recommended_crops)

        # (3) Build the processed data dictionary
        report_data = {
            "predictions": predictions,
            "crop_details": crop_details,
            "recommended_crops": crop_details,  # or a separate list
            "risk_assessment": risk_assessment,
            "mitigation_strategies": mitigation_strategies,
            "ai_alerts": ai_alerts,
            "next_best_action": next_best_action,
            "historical_weather": historical_weather,
            "regional_avg_yield": regional_avg_yield,
            "user_data": data,
            "future_climate": climate_forecast,
            "rotation_plan": rotation_plan,
        }
        # (4) Save this complete processed data in a dedicated field
        report_request.report_data = report_data
        report_request.save()

        # (5) Save the report_request ID in session for later PDF generation
        request.session["report_request_id"] = report_request.id

        return Response({
            "message": "Report request saved successfully. Please proceed to checkout to complete your payment.",
            "report_request_id": report_request.id
        }, status=status.HTTP_201_CREATED)



# --- Additional API Endpoints (unchanged) ---
class CropSuitabilityView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_data = request.data.copy()
        required_fields = ["ph_level", "temperature_2m", "moisture", "precipitation", "soil_type"]
        missing_fields = [field for field in required_fields if field not in user_data]
        if missing_fields:
            return Response({"error": f"Missing fields: {', '.join(missing_fields)}"}, status=status.HTTP_400_BAD_REQUEST)

        soil_data = {
            "ph_level": float(user_data.get("ph_level", 6.5)),
            "temperature_2m": float(user_data.get("temperature_2m", 20)),
            "moisture": float(user_data.get("moisture", 50)),
            "precipitation": float(user_data.get("precipitation", 30)),
            "soil_type": user_data.get("soil_type", "").strip().lower()
        }

        suitable_crops = get_suitable_crops(soil_data)
        if not suitable_crops:
            return Response({"message": "No suitable crops found for the given conditions."}, status=status.HTTP_200_OK)

        return Response({"suitable_crops": suitable_crops}, status=status.HTTP_200_OK)

class RiskAssessmentView(APIView):
    def post(self, request):
        soil_data = request.data.get("soil_attributes", {})
        if not soil_data:
            return Response({"error": "No soil data provided."}, status=status.HTTP_400_BAD_REQUEST)
        risks = evaluate_soil_risks(soil_data)
        return Response({"soil_risks": risks}, status=status.HTTP_200_OK)

class AIAlertsView(APIView):
    def post(self, request):
        weather_data = request.data.get("weather_data", {})
        if not weather_data:
            return Response({"error": "No weather data provided."}, status=status.HTTP_400_BAD_REQUEST)
        ai_alerts = generate_ai_alerts(weather_data)
        return Response({"ai_alerts": ai_alerts}, status=status.HTTP_200_OK)

class MitigationStrategiesView(APIView):
    def post(self, request):
        soil_data = request.data.get("soil_attributes", {})
        if not soil_data:
            return Response({"error": "No soil data provided."}, status=status.HTTP_400_BAD_REQUEST)
        strategies = generate_mitigation_strategies(soil_data)
        return Response({"mitigation_strategies": strategies}, status=status.HTTP_200_OK)

class NextBestActionView(APIView):
    def post(self, request):
        soil_data = request.data.get("soil_attributes", {})
        if not soil_data:
            return Response({"error": "No soil data provided."}, status=status.HTTP_400_BAD_REQUEST)
        suitable_crops = get_suitable_crops(soil_data)
        next_best_action = generate_next_best_action(soil_data, suitable_crops)
        return Response({"next_best_action": next_best_action}, status=status.HTTP_200_OK)


def request_soil_report(request):
    """Renders the request soil report page."""
    crops = CropSuitability.objects.all().order_by('name')
        # Optionally, extract unique soil types from the crops
    soil_types = set()
    for crop in crops:
        for soil in crop.suitable_soil_types:
            soil_types.add(soil)
    soil_types = sorted(list(soil_types))
    
    
    return render(request, "monetization/request_soil_report.html", {
        "crops": crops,
        "soil_types": soil_types
    })

# monetization/views/api_views.py
from rest_framework import status


class ReportStatusView(APIView):
    """
    Returns the status of a report request (PDF generation).
    - Returns "completed" if report_request.fulfilled is True.
    - Returns "processing" otherwise.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_id = request.GET.get('request_id')
        if not request_id:
            logger.error("No request id provided.")
            return Response(
                {"status": "error", "message": "No request id provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            request_id = int(request_id)
            report_request = ReportRequest.objects.get(id=request_id)
        except ReportRequest.DoesNotExist:
            logger.error("ReportRequest with id %s not found.", request_id)
            return Response(
                {"status": "error", "message": "Report request not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error("Invalid request id '%s': %s", request_id, e)
            return Response(
                {"status": "error", "message": "Invalid request id."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if report_request.fulfilled:
                return Response({"status": "completed"})
            else:
                return Response({"status": "processing"})
        except Exception as e:
            logger.error("Error checking status for request id %s: %s", request_id, e)
            return Response(
                {"status": "error", "message": "Internal server error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
                        
class FeedbackView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        data = request.data
        feedback_text = data.get("feedback_text", "").strip()
        email = data.get("email", "").strip() if data.get("email") else None
        if not feedback_text:
            return Response({"error": "Feedback text is required."}, status=status.HTTP_400_BAD_REQUEST)
        Feedback.objects.create(
            user=user,
            email=email,
            feedback_text=feedback_text
        )
        return Response({"message": "Feedback submitted successfully."}, status=status.HTTP_201_CREATED)




# --- New Dummy Page Views for Navigation ---
def overall_report(request):
    return render(request, "monetization/overall_report.html", {"message": "Overall Soil Report coming soon!"})

def crop_suitability_page(request):
    return render(request, "monetization/crop_suitability.html", {"message": "Crop Suitability Checker coming soon!"})

def risk_assessment_page(request):
    return render(request, "monetization/risk_assessment.html", {"message": "Risk Assessment coming soon!"})

def ai_alerts_page(request):
    return render(request, "monetization/ai_alerts.html", {"message": "AI Alerts & Mitigation Strategies coming soon!"})

def next_best_action_page(request):
    return render(request, "monetization/next_best_action.html", {"message": "Next Best Action Recommendations coming soon!"})
