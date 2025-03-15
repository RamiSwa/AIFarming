# views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.http import JsonResponse
from .models import WeatherData
from .serializers import WeatherDataSerializer
from .utils import fetch_weather_data_from_openmeteo, save_weather_data, geocode_location
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
import pandas as pd
import math
from django.utils import timezone
from datetime import datetime, timedelta
import requests
from django.conf import settings

# ---------------------------
# Test API endpoint (Public)
# ---------------------------
def test_api(request):
    return JsonResponse({"message": "API is working!"})


# ---------------------------
# Web View: Render Weather Page
# ---------------------------
@login_required
def weather_page(request):
    weather_data = WeatherData.objects.all().order_by('-time')[:50]  # Show last 50 records
    return render(request, 'weather/weather.html', {"weather_data": weather_data})


# ---------------------------
# Pagination for Weather Data API
# ---------------------------
class WeatherDataPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request) or self.page_size
        total_pages = math.ceil(self.page.paginator.count / page_size)
        return Response({
            'count': self.page.paginator.count,
            'total_pages': total_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


# ---------------------------
# API: Get Weather Data (Historical and/or Forecast)
# ---------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weather_data(request):
    """
    Retrieve weather data intelligently by combining stored historical data and forecast data.

    Allowed search parameters:
      - location (optional): if provided, data is filtered by location and forecast fetching is enabled.
      - start_date and end_date (optional): a date range in the format YYYY-MM-DD.
    
    Behavior:
      1. If no dates are provided, default to the last 7 days.
      2. If no location is provided:
            - Return stored data for the requested (or default) date range across all locations.
      3. If a location is provided:
            - If the range is entirely in the past (end_date ≤ today), return stored historical data.
            - If the range is entirely in the future (start_date > today), check for forecast data;
              if missing, fetch from Open‑Meteo, store it, then return it.
            - If the range spans both past and future, return stored historical data for the past portion and forecast data for the future portion (fetching forecast data if necessary), merge and return.
    """
    location = request.query_params.get('location', None)
    start_date = request.query_params.get('start_date', None)
    end_date = request.query_params.get('end_date', None)

    # If no dates provided, default to the last 7 days.
    if not start_date and not end_date:
        now = timezone.now()
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

    # Parse dates from strings to date objects.
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except Exception:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

    today = timezone.now().date()

    # ---------------------------
    # Case A: No location provided – search across all stored data.
    # ---------------------------
    if not location:
        stored_data = WeatherData.objects.all().filter(
            time__date__gte=start_date_obj, time__date__lte=end_date_obj
        ).order_by('-time')
        if not stored_data.exists():
            return Response({"error": "No matching weather data found."}, status=404)
        paginator = WeatherDataPagination()
        page = paginator.paginate_queryset(stored_data, request)
        serializer = WeatherDataSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # ---------------------------
    # Case B: Location provided – apply forecast/historical logic.
    # ---------------------------
    weather_query = WeatherData.objects.filter(original_location__iexact=location)

    # Case B1: Entirely Past (end_date ≤ today)
    if end_date_obj <= today:
        past_data = weather_query.filter(
            time__date__gte=start_date_obj, time__date__lte=end_date_obj
        ).order_by('-time')
        if not past_data.exists():
            return Response({"error": "No matching historical weather data found."}, status=404)
        paginator = WeatherDataPagination()
        page = paginator.paginate_queryset(past_data, request)
        serializer = WeatherDataSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # Case B2: Entirely Future (start_date > today)
    if start_date_obj > today:
        future_data = weather_query.filter(
            time__date__gte=start_date_obj, time__date__lte=end_date_obj
        ).order_by('time')
        if not future_data.exists():
            # Forecast data is not stored – fetch it.
            coordinates = geocode_location(location)
            if not coordinates:
                return Response({"error": "Could not fetch coordinates for this location."}, status=400)
            forecast_df = fetch_weather_data_from_openmeteo(coordinates["latitude"], coordinates["longitude"])
            if forecast_df.empty:
                return Response({"error": "No forecast data available."}, status=500)
            save_weather_data(forecast_df, original_location=location)
            # Re-query the forecast data.
            future_data = weather_query.filter(
                time__date__gte=start_date_obj, time__date__lte=end_date_obj
            ).order_by('time')
            if not future_data.exists():
                return Response({"error": "No matching forecast data found."}, status=404)
        paginator = WeatherDataPagination()
        page = paginator.paginate_queryset(future_data, request)
        serializer = WeatherDataSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # Case B3: Mixed Range (start_date ≤ today < end_date)
    if start_date_obj <= today < end_date_obj:
        past_data = weather_query.filter(
            time__date__gte=start_date_obj, time__date__lte=today
        ).order_by('-time')
        future_data = weather_query.filter(
            time__date__gte=(today + timedelta(days=1)), time__date__lte=end_date_obj
        ).order_by('time')
        if not future_data.exists():
            coordinates = geocode_location(location)
            if not coordinates:
                return Response({"error": "Could not fetch coordinates for this location."}, status=400)
            forecast_df = fetch_weather_data_from_openmeteo(coordinates["latitude"], coordinates["longitude"])
            if forecast_df.empty:
                return Response({"error": "No forecast data available."}, status=500)
            save_weather_data(forecast_df, original_location=location)
            future_data = weather_query.filter(
                time__date__gte=(today + timedelta(days=1)), time__date__lte=end_date_obj
            ).order_by('time')
        merged_data = list(past_data) + list(future_data)
        merged_data.sort(key=lambda x: x.time, reverse=True)
        serializer = WeatherDataSerializer(merged_data, many=True)
        return Response(serializer.data, status=200)

    return Response({"error": "Unhandled date range."}, status=400)



# ---------------------------
# API: Fetch & Store Weather Data
# ---------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def fetch_weather_for_location(request):
    location_name = request.data.get('location')
    if not location_name:
        return Response({'error': 'Location is required'}, status=400)
    coordinates = geocode_location(location_name)
    if not coordinates:
        return Response({'error': 'Could not fetch coordinates for this location'}, status=400)
    weather_data = fetch_weather_data_from_openmeteo(coordinates["latitude"], coordinates["longitude"])
    if weather_data.empty:
        return Response({'error': 'No weather data available'}, status=500)
    save_weather_data(weather_data, original_location=location_name)
    return Response({'message': 'Weather data fetched and saved successfully'}, status=200)


# ---------------------------
# API: Get Specific Weather Data by ID
# ---------------------------
@api_view(['GET'])
def get_weather_detail(request, pk):
    try:
        weather = WeatherData.objects.get(pk=pk)
        serializer = WeatherDataSerializer(weather)
        return Response(serializer.data)
    except WeatherData.DoesNotExist:
        return Response({"error": "Weather record not found."}, status=404)


# ---------------------------
# API: Update Weather Data by ID
# ---------------------------
@api_view(['PUT'])
def update_weather_data(request, pk):
    try:
        weather = WeatherData.objects.get(pk=pk)
        serializer = WeatherDataSerializer(weather, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    except WeatherData.DoesNotExist:
        return Response({"error": "Weather record not found."}, status=404)


# ---------------------------
# API: Delete Weather Data by ID
# ---------------------------
@api_view(['DELETE'])
def delete_weather_data(request, pk):
    try:
        weather = WeatherData.objects.get(pk=pk)
        weather.delete()
        return Response({"message": "Weather record deleted successfully."}, status=200)
    except WeatherData.DoesNotExist:
        return Response({"error": "Weather record not found."}, status=404)


# ---------------------------
# Web View: Weather Dashboard
# ---------------------------
@login_required
def weather_dashboard(request):
    weather_data = WeatherData.objects.all().order_by('-time')[:50]
    return render(request, 'weather/weather_dashboard.html', {'weather_data': weather_data})


# ---------------------------
# API: Get 7-Day Future Weather Forecast
# ---------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weather_forecast(request):
    location_name = request.query_params.get("location", None)
    if not location_name:
        return Response({"error": "Location is required"}, status=400)
    coordinates = geocode_location(location_name)
    if not coordinates:
        return Response({"error": "Could not fetch coordinates for this location"}, status=400)
    weather_data = fetch_weather_data_from_openmeteo(coordinates["latitude"], coordinates["longitude"])
    if weather_data.empty:
        return Response({"error": "No weather forecast available."}, status=500)
    weather_data["time"] = pd.to_datetime(weather_data["time"], utc=True)
    now_utc = pd.Timestamp.now(tz="UTC").normalize()
    future_data = weather_data[weather_data["time"] >= now_utc]
    future_data["date"] = future_data["time"].dt.date
    daily_forecast = future_data.groupby("date").apply(lambda x: x.iloc[12] if len(x) > 12 else x.iloc[0]).reset_index(drop=True)
    def classify_weather(temp, precipitation, humidity, wind_speed):
        if precipitation > 2:
            return "Rainy"
        elif precipitation > 0.5:
            return "Drizzle"
        elif temp < 0 and precipitation > 0.2:
            return "Snowy"
        elif temp < 0:
            return "Cold"
        elif humidity > 90 and wind_speed < 5:
            return "Foggy"
        elif wind_speed > 25:
            return "Windy"
        elif temp > 35:
            return "Extremely Hot"
        elif temp > 30:
            return "Hot"
        elif temp > 25:
            return "Warm"
        elif temp > 18:
            return "Mild"
        elif temp > 10:
            return "Cool"
        elif humidity > 75 and precipitation == 0:
            return "Humid"
        elif 65 <= humidity < 75 and wind_speed < 10:
            return "Partly Cloudy"
        elif humidity < 65 and precipitation == 0 and wind_speed < 8:
            return "Clear"
        elif 50 <= humidity < 65 and wind_speed > 10:
            return "Breezy"
        else:
            return "Cloudy"
    daily_forecast["weather_description"] = daily_forecast.apply(
        lambda row: classify_weather(row["temperature_2m"], row["precipitation"], row["relative_humidity_2m"], row["wind_speed_10m"]), axis=1
    )
    forecast_data = daily_forecast.to_dict(orient="records")
    return Response(forecast_data, status=200)


# ---------------------------
# Home Page: Future Weather Forecast
# ---------------------------
def home_page(request):
    return render(request, "weather/home.html")
