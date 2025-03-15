
# recommendations/models.py:

from django.db import models
from django.conf import settings
from soil.models import SoilData
from weather.models import WeatherData

class Crop(models.Model):
    name = models.CharField(max_length=50, unique=True)
    min_temp = models.FloatField()
    max_temp = models.FloatField()
    max_precipitation = models.FloatField(default=50.0)
    min_soil_temp = models.FloatField(default=10.0)
    
    # ✅ New: Preferred Growing Season (list of months)
    PREFERRED_GROWING_SEASONS = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December"),
    ]
    
    preferred_growing_season = models.JSONField(default=list, blank=True, help_text="List of preferred months [1-12].")
    
    def __str__(self):
        return self.name

class Recommendation(models.Model):
    """
    Stores AI-generated crop recommendations based on soil & weather data.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    soil_data = models.ForeignKey(SoilData, on_delete=models.CASCADE, related_name="recommendations")
    weather_data = models.ForeignKey(WeatherData, on_delete=models.SET_NULL, null=True, blank=True, related_name="recommendations")
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name="recommendations")
    
    recommended_crops = models.JSONField(help_text="AI-recommended crops based on soil & weather conditions.")
    expected_yield = models.FloatField(null=True, blank=True, help_text="Predicted yield in kg/ha.")
    risk_assessment = models.TextField(null=True, blank=True, help_text="Warnings for drought, frost, or other risks.")
    optimal_planting_time = models.CharField(max_length=50, help_text="Best planting window: Early, Mid, Late Season.")
    
    ai_model_version = models.JSONField(default=dict, blank=True, help_text="Dynamically fetched AI model versions.")

    created_at = models.DateTimeField(auto_now_add=True)
    
    predicted_soil_temp = models.FloatField(null=True, blank=True, help_text="Predicted soil temperature in °C.")

    # ✅ NEW: Store AI-generated predicted yield before adjustments
    predicted_yield = models.FloatField(null=True, blank=True, help_text="AI-predicted raw yield in kg/ha.")
    


    
    confidence_score = models.JSONField(null=True, blank=True, help_text="Model confidence scores for predictions.")
    weather_summary = models.TextField(null=True, blank=True, help_text="Brief summary of weather conditions.")
    yield_explanation = models.JSONField(default=list, blank=True, help_text="Explanation of yield adjustments.")
    mitigation_suggestions = models.JSONField(default=list, blank=True, help_text="Suggestions to improve yield.")
    historical_trends = models.JSONField(default=list, blank=True, help_text="Past weather trends for analysis.")
    alerts = models.JSONField(default=list, blank=True, help_text="Important alerts related to the recommendation.")
    next_best_action = models.TextField(null=True, blank=True, help_text="Suggested next step for the farmer.")
    alternative_farming_advice = models.JSONField(default=list, blank=True, help_text="General farming tips.")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['soil_data']),
            models.Index(fields=['weather_data']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Recommendation for {self.user.email} - {self.created_at.strftime('%Y-%m-%d')}"

