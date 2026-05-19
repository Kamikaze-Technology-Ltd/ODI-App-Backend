from rest_framework import serializers
from athens.models import Profile
from .models import Trip, TripStatus


class InspectorSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.id', read_only=True)

    class Meta:
        model = Profile
        fields = ['user_id', 'full_name', 'profile_picture']


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
