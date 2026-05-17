from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from athens.utils import upload_image
from dispatch.models import Trip, TripStatus
from .models import QueryResponse


def validate_is_file(value):
    if not isinstance(value, UploadedFile):
        raise serializers.ValidationError("A valid file must be uploaded. Plain text is not accepted.")
    return value


class QueryResponseSerializer(serializers.ModelSerializer):
    photo_file = serializers.ImageField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload query photo (jpg/png)"
    )
    photo = serializers.URLField(read_only=True, required=False)
    trip_id = serializers.CharField(write_only=True, help_text="The trip_id of the trip")

    class Meta:
        model = QueryResponse
        fields = [
            'id', 'estimated_time_arrival', 'current_status',
            'additional_notes', 'your_response', 'trip_id',
            'photo', 'photo_file',
        ]
        read_only_fields = ('id',)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['trip_id'] = instance.trip.trip.trip_id if instance.trip and instance.trip.trip else None
        return data

    def validate_trip_id(self, value):
        try:
            trip = Trip.objects.get(trip_id=value)
        except Trip.DoesNotExist:
            raise serializers.ValidationError(f"Trip with trip_id '{value}' does not exist.")
        trip_status, _ = TripStatus.objects.get_or_create(
            trip=trip,
            defaults={'current_status': 'started'},
        )
        return trip_status

    def _handle_upload(self, validated_data):
        photo_file = validated_data.pop('photo_file', None)
        if photo_file:
            url = upload_image(photo_file, folder='query_photos')
            if not url:
                raise serializers.ValidationError({'photo_file': 'Upload failed. Check Cloudinary credentials.'})
            validated_data['photo'] = url
        return validated_data

    def create(self, validated_data):
        validated_data = self._handle_upload(validated_data)
        trip_status = validated_data.pop('trip_id', None)
        if trip_status:
            validated_data['trip'] = trip_status
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._handle_upload(validated_data)
        trip_status = validated_data.pop('trip_id', None)
        if trip_status:
            validated_data['trip'] = trip_status
        if 'photo' in validated_data:
            instance.photo = validated_data.pop('photo')
            instance.save()
        return super().update(instance, validated_data)
