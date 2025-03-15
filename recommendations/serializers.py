from rest_framework import serializers
from .models import Recommendation, Crop
from weather.serializers import WeatherDataSerializer


class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = ["id", "name", "min_temp", "max_temp", "max_precipitation", "min_soil_temp"]

class RecommendationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    crop = CropSerializer()
    weather_data = WeatherDataSerializer() 
    
    class Meta:
        model = Recommendation
        fields = '__all__'

class RecommendationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = [
            "user", "crop", "recommended_crops", "expected_yield", "risk_assessment",
            "optimal_planting_time", "ai_model_version"
        ]
        
        
class RecommendationExportSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    crop = serializers.CharField(source="crop.name")  # Returns just the name

    class Meta:
        model = Recommendation
        fields = [
            "user", "crop", "expected_yield", "predicted_yield", "predicted_soil_temp",
            "risk_assessment", "optimal_planting_time",
            "weather_summary", "next_best_action", "ai_model_version", "created_at"
        ]