from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from athens.utils import upload_image
from dispatch.models import Trip
from .models import Reports


def validate_is_file(value):
    if not isinstance(value, UploadedFile):
        raise serializers.ValidationError("A valid file must be uploaded. Plain text is not accepted.")
    return value


class ReportsSerializer(serializers.ModelSerializer):
    photo_file = serializers.ImageField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload report photo (jpg/png)"
    )
    photo = serializers.URLField(read_only=True, required=False)
    trip_id = serializers.CharField(write_only=True, help_text="The trip_id of the trip")

    class Meta:
        model = Reports
        fields = ['id', 'reason', 'message', 'photo', 'photo_file', 'trip_id']
        read_only_fields = ('id',)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['trip_id'] = instance.trip.trip_id if instance.trip else None
        return data

    def validate_trip_id(self, value):
        try:
            trip = Trip.objects.get(trip_id=value)
        except Trip.DoesNotExist:
            raise serializers.ValidationError(f"Trip with trip_id '{value}' does not exist.")
        return trip

    def _handle_upload(self, validated_data):
        photo_file = validated_data.pop('photo_file', None)
        if photo_file:
            url = upload_image(photo_file, folder='reports')
            if not url:
                raise serializers.ValidationError({'photo_file': 'Upload failed. Check Cloudinary credentials.'})
            validated_data['photo'] = url
        return validated_data

    def create(self, validated_data):
        validated_data = self._handle_upload(validated_data)
        trip = validated_data.pop('trip_id', None)
        if trip:
            validated_data['trip'] = trip
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._handle_upload(validated_data)
        trip = validated_data.pop('trip_id', None)
        if trip:
            validated_data['trip'] = trip
        if 'photo' in validated_data:
            instance.photo = validated_data.pop('photo')
            instance.save()
        return super().update(instance, validated_data)
