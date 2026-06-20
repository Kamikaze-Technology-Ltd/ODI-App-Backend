from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from athens.utils import upload_image
from dispatch.models import Trip
from .models import Inspection, Rejection


def validate_is_file(value):
    if not isinstance(value, UploadedFile):
        raise serializers.ValidationError("A valid file must be uploaded. Plain text is not accepted.")
    return value


class InspectionSerializer(serializers.ModelSerializer):
    photo_file = serializers.ImageField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload inspection photo (jpg/png)"
    )
    photo = serializers.URLField(read_only=True, required=False)
    trip_id = serializers.CharField(write_only=True, help_text="The trip_id of the trip")
    inspector_id = serializers.CharField(source='inspector.id', read_only=True)

    class Meta:
        model = Inspection
        fields = [
            'id', 'inspector_id', 'trip_id',
            'valid_documentation', 'tank_seals_intact', 'safe_operating_condition',
            'fire_extinguisher', 'license_verified',
            'notes', 'photo', 'photo_file', 'decision',
            'created_at', 'updated_at',
        ]
        read_only_fields = ('id', 'inspector_id', 'created_at', 'updated_at')

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
            url = upload_image(photo_file, folder='inspection_photos')
            if not url:
                raise serializers.ValidationError({'photo_file': 'Upload failed. Check Cloudinary credentials.'})
            validated_data['photo'] = url
        return validated_data

    def create(self, validated_data):
        validated_data = self._handle_upload(validated_data)
        trip = validated_data.pop('trip_id', None)
        if trip:
            validated_data['trip'] = trip
        user = self.context['request'].user
        if user.role != 'inspector':
            raise serializers.ValidationError({'inspector': 'Only users with role=inspector can create inspections.'})
        validated_data['inspector'] = user
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


class RejectionSerializer(serializers.ModelSerializer):
    photo_file = serializers.ImageField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload rejection photo (jpg/png)"
    )
    photo = serializers.URLField(read_only=True, required=False)
    inspection_id = serializers.CharField(write_only=True, help_text="The id of the inspection being rejected")

    class Meta:
        model = Rejection
        fields = [
            'id', 'inspection_id', 'reason', 'situation_report',
            'photo', 'photo_file', 'created_at', 'updated_at',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['inspection_id'] = instance.inspection.id if instance.inspection else None
        return data

    def validate_inspection_id(self, value):
        try:
            inspection = Inspection.objects.get(id=value)
        except Inspection.DoesNotExist:
            raise serializers.ValidationError(f"Inspection with id '{value}' does not exist.")
        return inspection

    def _handle_upload(self, validated_data):
        photo_file = validated_data.pop('photo_file', None)
        if photo_file:
            url = upload_image(photo_file, folder='rejection_photos')
            if not url:
                raise serializers.ValidationError({'photo_file': 'Upload failed. Check Cloudinary credentials.'})
            validated_data['photo'] = url
        return validated_data

    def create(self, validated_data):
        validated_data = self._handle_upload(validated_data)
        inspection = validated_data.pop('inspection_id', None)
        if inspection:
            validated_data['inspection'] = inspection
            inspection.decision = 'rejected'
            inspection.save()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._handle_upload(validated_data)
        inspection = validated_data.pop('inspection_id', None)
        if inspection:
            validated_data['inspection'] = inspection
        if 'photo' in validated_data:
            instance.photo = validated_data.pop('photo')
            instance.save()
        return super().update(instance, validated_data)
