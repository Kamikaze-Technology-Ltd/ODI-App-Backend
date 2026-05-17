from rest_framework import serializers
from .models import Trip, TripStatus


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class TripStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripStatus
        fields = '__all__'
        read_only_fields = ('id', 'trip', 'created_at', 'updated_at')
