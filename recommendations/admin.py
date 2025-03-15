from django.contrib import admin
from django.http import HttpResponse
import csv
import json  # ✅ Needed for parsing JSON
from .models import Crop, Recommendation


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ("name", "min_temp", "max_temp", "max_precipitation", "min_soil_temp")
    search_fields = ("name",)
    list_filter = ("min_temp", "max_temp", "max_precipitation")


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "user", "crop", "expected_yield", "predicted_yield", "predicted_soil_temp",
        "risk_assessment", "optimal_planting_time", "confidence_score", "weather_summary",
        "next_best_action", "created_at", "formatted_ai_model_version"  # ✅ Updated field
    )
    search_fields = ("user__email", "crop__name", "ai_model_version")
    list_filter = ("optimal_planting_time", "ai_model_version", "created_at", "risk_assessment")
    readonly_fields = ("created_at",)
    actions = ["export_as_csv"]

    def formatted_ai_model_version(self, obj):
        """
        Converts JSON model versions into a human-readable format.
        """
        try:
            versions = json.loads(obj.ai_model_version)  # ✅ Convert JSON string to a Python dictionary
            return " | ".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in versions.items())
        except (json.JSONDecodeError, TypeError):
            return str(obj.ai_model_version)  # If not JSON, return as is

    formatted_ai_model_version.short_description = "AI Model Version"  # ✅ Admin panel column name

    def export_as_csv(self, request, queryset):
        """
        Exports selected recommendations as a CSV file with the new fields included.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="recommendations.csv"'
        writer = csv.writer(response)
        
        writer.writerow([
            "User", "Crop", "Expected Yield", "Predicted Yield", "Predicted Soil Temp",
            "Risk Assessment", "Optimal Planting Time", "Confidence Score",
            "Weather Summary", "Next Best Action", "AI Model Version", "Created At"
        ])
        
        for recommendation in queryset:
            writer.writerow([
                recommendation.user.email,
                recommendation.crop.name if recommendation.crop else "N/A",
                recommendation.expected_yield,
                recommendation.predicted_yield,
                recommendation.predicted_soil_temp,
                recommendation.risk_assessment,
                recommendation.optimal_planting_time,
                recommendation.confidence_score,
                recommendation.weather_summary,
                recommendation.next_best_action,
                self.formatted_ai_model_version(recommendation),  # ✅ Use formatted version
                recommendation.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    
    export_as_csv.short_description = "Export Selected as CSV"
