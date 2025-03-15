from rest_framework import serializers
from .models import WeatherData


class WeatherDataSerializer(serializers.ModelSerializer):
    precip_30day_sum = serializers.SerializerMethodField()
    class Meta:
        model = WeatherData
        fields = [
            "id",
            "time",
            "original_location",
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "precipitation",
            "precip_30day_sum",
            "location",
            "latitude",
            "longitude",
            "last_updated",
        ]


    def get_precip_30day_sum(self, obj):
        return obj.get_precip_30day_sum()
