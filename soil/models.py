# soil/models.py:

from django.db import models
from django.conf import settings  # ✅ Import user model

class SoilData(models.Model):
    # ✅ Link soil data to user accounts (Farmer who added the data)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="soil_data", null=True, blank=True)

    time = models.DateTimeField(db_index=True)  # ✅ Indexed for fast queries
    original_location = models.CharField(max_length=100, blank=True, null=True)  # ✅ Stores city name, not just coordinates
    soil_temp_0_to_7cm = models.FloatField(null=True, blank=True)  # ✅ Now allows null (for missing sensor data)
    soil_temp_7_to_28cm = models.FloatField(null=True, blank=True)
    moisture = models.FloatField(null=True, blank=True)  # ✅ New field (Moisture %)
    ph_level = models.FloatField(null=True, blank=True)  # ✅ New field (pH Level)
    nitrogen = models.FloatField(null=True, blank=True)  # ✅ Future AI Training (NPK Levels)
    phosphorus = models.FloatField(null=True, blank=True)
    potassium = models.FloatField(null=True, blank=True)

    location = models.CharField(max_length=100, db_index=True)  # ✅ Indexed for faster filtering
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    
    last_updated = models.DateTimeField(auto_now=True)  # ✅ Track last update timestamp

    # ✅ Track data source (Manual, CSV, API, Sensor)
    DATA_SOURCE_CHOICES = [
        ("manual", "Manual Entry"),
        ("csv", "CSV Upload"),
        ("api", "Weather API"),
        ("sensor", "IoT Sensor"),
    ]
    data_source = models.CharField(max_length=10, choices=DATA_SOURCE_CHOICES, default="manual")

    # ✅ Identify which sensor provided the data
    SENSOR_TYPE_CHOICES = [
        ("temperature", "Temperature Sensor"),
        ("moisture", "Moisture Sensor"),
        ("ph", "pH Sensor"),
        ("nutrients", "NPK Sensor"),
        ("multi", "Multi-Sensor Device"),  # ✅ NEW: Supports devices that provide ALL readings
    ]
    sensor_type = models.CharField(max_length=20, choices=SENSOR_TYPE_CHOICES, null=True, blank=True)

    # ✅ Track specific sensor ID (important for multiple sensors)
    sensor_id = models.CharField(max_length=50, null=True, blank=True)  # ✅ Unique ID for each sensor device

    class Meta:
        ordering = ['-time']  # ✅ Sort by most recent time first
        indexes = [
            models.Index(fields=['time']),  # ✅ Optimized time-based lookups
            models.Index(fields=['location']),  # ✅ Faster filtering by location
            models.Index(fields=['latitude', 'longitude']),  # ✅ Optimized for geo-based queries
            models.Index(fields=['user']),  # ✅ Faster filtering by user
            models.Index(fields=['sensor_type']),  # ✅ Faster filtering by sensor type
            models.Index(fields=['sensor_id']),  # ✅ Faster filtering by sensor ID
        ]
    
    def __str__(self):
        return f"Soil Data at {self.time} for {self.original_location or self.location}"
