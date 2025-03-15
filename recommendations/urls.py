from django.urls import path
from .views import (
    recommendations_page,
    fetch_results,  # ✅ New View
    manage_recommendations,  # ✅ New View
    csv_upload,  # ✅ New View
    RecommendationPredictAPIView,
    RecommendationListCreateAPIView,
    RecommendationDetailAPIView,
    FileUploadAPIView,
    TaskStatusAPIView,
    CropListAPIView,
    RecommendationExportAPIView,
    RecommendationExportPreviewAPIView, 
    RecommendationSummaryAPIView,
    SampleRecommendationsCSVDownloadAPIView,
    TemperatureTrendsChartDataAPIView,
    PredictedYieldChartDataAPIView,
    WeatherSuitabilityChartDataAPIView,
)

urlpatterns = [
    # ✅ Web page for recommendations
    path("", recommendations_page, name="recommendations_page"),


    # ✅ Internal Navigation for Sections
    path("recommendations/fetch/", fetch_results, name="fetch_results"),
    path("recommendations/manage/", manage_recommendations, name="manage_recommendations"),
    path("recommendations/upload/", csv_upload, name="csv_upload"),
    

    # ✅ API to predict recommendations
    path("api/predict/", RecommendationPredictAPIView.as_view(), name="recommendation_predict"),

    # ✅ API to list and create recommendations
    path("api/recommendations/", RecommendationListCreateAPIView.as_view(), name="recommendation_list_create"),


    # ✅ API to retrieve or delete a specific recommendation
    path("api/recommendations/<int:pk>/", RecommendationDetailAPIView.as_view(), name="recommendation_detail"),


    path("api/recommendations/export/", RecommendationExportAPIView.as_view(), name="recommendation_export"),
    path("api/recommendations/export/preview/", RecommendationExportPreviewAPIView.as_view(), name="recommendation_export_preview"),
    

    # ✅ API to upload recommendation data via CSV
    path("api/upload/", FileUploadAPIView.as_view(), name="file_upload"),
    
    path("task-status/<str:task_id>/", TaskStatusAPIView.as_view(), name="task_status"),
    
    # ✅ API to list available crops
    path("api/crops/", CropListAPIView.as_view(), name="crop_list"),


    path("api/summary/", RecommendationSummaryAPIView.as_view(), name="recommendation_summary"),


    # ... other URL patterns
    path('api/sample-csv/', SampleRecommendationsCSVDownloadAPIView.as_view(), name='sample_csv'),
    
    
    # API ENDPOINTS for Chart Data Aggregation
    path("api/charts/temperature-trends/", TemperatureTrendsChartDataAPIView.as_view(), name="chart_temperature_trends"),
    path("api/charts/predicted-yield/", PredictedYieldChartDataAPIView.as_view(), name="chart_predicted_yield"),
    path("api/charts/weather-suitability/", WeatherSuitabilityChartDataAPIView.as_view(), name="chart_weather_suitability"),

]
