from rest_framework import serializers
from .models import SoilData

class SoilDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoilData
        fields = '__all__'
