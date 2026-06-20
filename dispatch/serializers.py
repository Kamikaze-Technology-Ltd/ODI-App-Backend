from rest_framework import serializers
from athens.models import Profile
from .models import Trip, TripStatus


class InspectorSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='user.id', read_only=True)

    class Meta:
        model = Profile
        fields = ['user_id', 'full_name', 'profile_picture']


class TripSerializer(serializers.ModelSerializer):
    inspection_status = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_inspection_status(self, obj):
        status_obj = getattr(obj, 'inspection_status', None)
        return status_obj.inspection_status if status_obj else 'pending'


class TripStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripStatus
        fields = '__all__'
        read_only_fields = ('id', 'trip', 'created_at', 'updated_at')
