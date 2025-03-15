from django.urls import path
from .views import (
    test_api,
    weather_page,
    get_weather_data,
    fetch_weather_for_location,
    get_weather_detail,
    update_weather_data,
    delete_weather_data,
    weather_dashboard,
    get_weather_forecast,
    
)

urlpatterns = [
    path("test/", test_api, name="test_api"),  # Check API status
    path("dashboard/", weather_dashboard, name="weather_dashboard"),  # Web view
    path("", weather_page, name="weather_page"),  # Weather page

    path("api/forecast/", get_weather_forecast, name="get_weather_forecast"),


    # API Endpoints
    path("api/data/", get_weather_data, name="get_weather_data"),
    path("api/fetch/", fetch_weather_for_location, name="fetch_weather_for_location"),
    path("api/data/<int:pk>/", get_weather_detail, name="get_weather_detail"),
    path("api/data/<int:pk>/update/", update_weather_data, name="update_weather_data"),
    path("api/data/<int:pk>/delete/", delete_weather_data, name="delete_weather_data"),


]
