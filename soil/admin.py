from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import SoilData

@admin.register(SoilData)
class SoilDataAdmin(admin.ModelAdmin):
    list_display = (
        'time', 
        'user',  # ✅ Show user who entered the data
        'original_location', 
        'soil_temp_0_to_7cm', 
        'soil_temp_7_to_28cm', 
        'moisture',  # ✅ Display moisture level
        'ph_level',  # ✅ Display pH level
        'nitrogen', 'phosphorus', 'potassium',  # ✅ NPK Levels
        'location', 
        'latitude', 
        'longitude',
        'data_source',  # ✅ Show how the data was added (Manual, CSV, API, Sensor)
        'sensor_type',  # ✅ New: Show sensor type (if from a sensor)
        'sensor_id',  # ✅ New: Show which sensor provided the data
        'last_updated'
    )
    
    list_filter = (
        'original_location', 
        'time', 
        'last_updated', 
        'data_source',  # ✅ Filter by how the data was added
        'sensor_type'  # ✅ Filter by type of sensor used
    )
    
    search_fields = ('original_location', 'location', 'user__email', 'sensor_id')  # ✅ Allow search by sensor ID
    ordering = ('-time',)  # ✅ Order records by the most recent time
    actions = ['export_as_csv']  # ✅ Add CSV export action

    def export_as_csv(self, request, queryset):
        """
        Custom admin action to export selected soil data records to CSV.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="soil_data.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Time', 'User', 'Original Location', 'Soil Temp (0-7 cm)', 'Soil Temp (7-28 cm)',
            'Moisture (%)', 'pH Level', 'Nitrogen', 'Phosphorus', 'Potassium', 
            'Location', 'Latitude', 'Longitude', 'Data Source', 'Sensor Type', 'Sensor ID', 'Last Updated'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.time, 
                obj.user.email if obj.user else "N/A",  # ✅ Show user email
                obj.original_location or obj.location, 
                obj.soil_temp_0_to_7cm, 
                obj.soil_temp_7_to_28cm, 
                obj.moisture, obj.ph_level, obj.nitrogen, obj.phosphorus, obj.potassium,
                obj.location, obj.latitude, obj.longitude,
                obj.data_source, obj.sensor_type or "N/A", obj.sensor_id or "N/A", obj.last_updated
            ])

        return response

    export_as_csv.short_description = "Export Selected to CSV"
