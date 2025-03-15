from datetime import timedelta
from django.db import models
from django.db.models import Sum


class WeatherData(models.Model):
    time = models.DateTimeField(db_index=True)  # ✅ Index for fast time-based queries
    original_location = models.CharField(max_length=100, blank=True, null=True)
    temperature_2m = models.FloatField()
    relative_humidity_2m = models.FloatField()
    wind_speed_10m = models.FloatField()
    precipitation = models.FloatField()
    location = models.CharField(max_length=100, db_index=True)  # ✅ Index for location-based queries
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True, db_index=True)  # ✅ Index for sorting by latest updates

    class Meta:
        ordering = ['-last_updated', '-time']  # ✅ Always fetch latest entries first
        indexes = [
            models.Index(fields=['location', 'time']),  # ✅ Speeds up location+time queries
            models.Index(fields=['-last_updated', '-time']),  # ✅ Optimized for latest records
        ]

    def __str__(self):
        return f"{self.original_location or self.location} at {self.time}"


    # ✅ NEW: Compute precipitation over the last 30 days
    def get_precip_30day_sum(self):
        last_30_days = self.time - timedelta(days=30)
        total_precip = WeatherData.objects.filter(
            location=self.location, 
            time__gte=last_30_days, time__lte=self.time
        ).aggregate(Sum('precipitation'))['precipitation__sum'] or 0
        return total_precip
    
    
    
"""
### **📌 Summary of What We Need to Do (Step-by-Step)**

#### **1️⃣ User Submits a Report Request**
- User enters **location & soil data**.
- If latitude & longitude **aren’t provided**, we **geocode the location**.
- If critical soil data is **missing**, we **fetch weather data** to complete it.

#### **2️⃣ Validate & Process Data**
- Ensure **all required fields are present**.
- Validate **numerical ranges** for soil & weather data.
- If `soil_temp_0_to_7cm` is missing, **fetch it from Open-Meteo**.

#### **3️⃣ Save Data to Database**
- Save **validated soil data** into DB.
- Check for **existing weather data** in DB.
- If missing, **fetch & save new weather data**.

#### **4️⃣ Run AI Model Predictions**
- Preprocess data using a **feature engineering pipeline**.
- Predict **soil temperature** using local AI models.
- **No AI crop recommendations yet**—instead, use **basic inference-based recommendations**.

#### **5️⃣ Generate Report**
- Format **AI predictions & insights**.
- Include **charts & visual analytics**.
- Save the **generated report in DB**.

---

"""