from django.urls import path
from .views import (
    SoilDataAPIView,
    SoilDataDetailAPIView,
    SoilDataFetchAPIView,
    SoilDataExportAPIView,
    ManualSoilDataEntryAPIView,  # ✅ Added manual entry API
    CSVUploadAPIView,  # ✅ Added CSV upload API
    SensorDataIngestionAPIView,  # ✅ Added Sensor data API
    soil_dashboard,
    SampleCSVDownloadAPIView,
    GeocodeAPIView,
)

urlpatterns = [
    # ✅ Soil Data APIs
    path('api/data/', SoilDataAPIView.as_view(), name='soil-data-list'),
    path('api/data/<int:pk>/', SoilDataDetailAPIView.as_view(), name='soil-data-detail'),
    
    # ✅ Fetch Live Soil Data (from external API)
    path('api/fetch/', SoilDataFetchAPIView.as_view(), name='soil-data-fetch'),
    
    # ✅ Export Soil Data as CSV
    path('api/export/', SoilDataExportAPIView.as_view(), name='soil-data-export'),
    
    # ✅ Manual Data Entry (New)
    path('api/manual-entry/', ManualSoilDataEntryAPIView.as_view(), name='manual-soil-entry'),
    
    # ✅ CSV Upload (New)
    path('api/upload-csv/', CSVUploadAPIView.as_view(), name='upload-csv'),
    
    # ✅ Sensor Data Ingestion (New)
    path('api/sensor-data/', SensorDataIngestionAPIView.as_view(), name='sensor-data-ingestion'),

    # ✅ Dashboard View
    path('soil_dashboard/', soil_dashboard, name='soil-dashboard'),
    
    
    
    path('api/download-sample-csv/', SampleCSVDownloadAPIView.as_view(), name='download-sample-csv'),


    path('api/geocode/', GeocodeAPIView.as_view(), name='geocode-api'),

]
