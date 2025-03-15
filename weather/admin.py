from django.contrib import admin
from .models import WeatherData

@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = ('time', 'original_location', 'latitude', 'longitude', 'temperature_2m', 
                    'relative_humidity_2m', 'wind_speed_10m', 'precipitation', 'get_precip_30day_sum', 
                    'last_updated')
    
    list_filter = ('original_location', 'time', 'last_updated')
    search_fields = ('original_location', 'location')
    ordering = ('-time', '-id')

    # ✅ Add computed precipitation as a read-only field
    def get_precip_30day_sum(self, obj):
        return obj.get_precip_30day_sum()
    
    get_precip_30day_sum.short_description = "Precip. Last 30 Days"
