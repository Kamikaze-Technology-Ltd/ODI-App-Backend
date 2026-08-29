"""Serializers for the driver-side catalogue + dispense log endpoints."""

from rest_framework import serializers

from athens.models import Profile
from dispatch.models import Trip

from .models import DispenseLog, EmergencyContact, QuickReply, ReportReason


class DispenseLogSerializer(serializers.ModelSerializer):
    trip_id = serializers.CharField(source="trip.trip_id", read_only=True)
    truck_no = serializers.CharField(source="trip.truck_no", read_only=True)
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = DispenseLog
        fields = [
            "id", "trip_id", "truck_no", "driver_name", "station", "product_type",
            "opening_reading", "closing_reading", "volume_dispensed",
            "notes", "photo", "dispensed_at",
        ]
        read_only_fields = ["id", "dispensed_at", "volume_dispensed"]

    def get_driver_name(self, obj):
        if not obj.driver:
            return ""
        profile = Profile.objects.filter(user=obj.driver).first()
        return profile.full_name if profile else obj.driver.phone_number


class CreateDispenseLogSerializer(serializers.Serializer):
    trip_id = serializers.CharField()
    station = serializers.CharField(required=False, allow_blank=True)
    product_type = serializers.CharField(required=False, allow_blank=True)
    opening_reading = serializers.IntegerField(required=False, default=0)
    closing_reading = serializers.IntegerField(required=False, default=0)
    volume_dispensed = serializers.IntegerField(required=False, default=0)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    photo = serializers.URLField(required=False, allow_blank=True)

    def validate_trip_id(self, value):
        trip = Trip.objects.filter(trip_id=value).first()
        if trip is None:
            raise serializers.ValidationError(f"Trip '{value}' does not exist.")
        return trip


class QuickReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickReply
        fields = ["id", "text", "audience", "position"]


class ReportReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportReason
        fields = ["id", "key", "label", "position"]


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["id", "key", "label", "phone_number", "description", "position"]
