"""Serializers for the Inspector app.

Every payload is shaped the way the mobile screens consume it, so the client
never has to stitch three endpoints together to render one card.
"""

from django.contrib.auth import authenticate
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from athens.models import OTPCode, Profile, User
from athens.utils import upload_image
from dispatch.models import Trip
from inspection.models import Inspection, InspectionStatus, Rejection

from .models import (
    Alert,
    AlertEvent,
    AppNotification,
    InspectorProfile,
    InspectorQuery,
    NotificationPreference,
    Shift,
    generate_badge_id,
)


def validate_is_file(value):
    if not isinstance(value, UploadedFile):
        raise serializers.ValidationError("A valid file must be uploaded. Plain text is not accepted.")
    return value


# ─────────────────────────── Identity ───────────────────────────


class InspectorProfileSerializer(serializers.ModelSerializer):
    """Everything the Profile screen renders, flattened."""

    user_id = serializers.CharField(source="user.id", read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    rank_label = serializers.SerializerMethodField()
    current_shift = serializers.SerializerMethodField()

    class Meta:
        model = InspectorProfile
        fields = [
            "id", "user_id", "badge_id", "rank", "rank_label", "zone", "depot",
            "clearance_level", "vehicles_cleared", "is_on_duty", "is_verified",
            "active_since", "full_name", "email", "phone_number",
            "profile_picture", "current_shift", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user_id", "badge_id", "vehicles_cleared", "created_at", "updated_at"]

    def _profile(self, obj):
        return Profile.objects.filter(user=obj.user).first()

    def get_full_name(self, obj):
        profile = self._profile(obj)
        return profile.full_name if profile else ""

    def get_email(self, obj):
        profile = self._profile(obj)
        return profile.email if profile else ""

    def get_phone_number(self, obj):
        return obj.user.phone_number

    def get_profile_picture(self, obj):
        profile = self._profile(obj)
        return profile.profile_picture if profile else None

    def get_rank_label(self, obj):
        return obj.get_rank_display()

    def get_current_shift(self, obj):
        shift = Shift.objects.filter(inspector=obj.user).exclude(status="ended").first()
        return ShiftSerializer(shift).data if shift else None


class InspectorSignupSerializer(serializers.Serializer):
    """Create your Inspector Account."""

    full_name = serializers.CharField()
    phone_number = serializers.CharField()
    email = serializers.EmailField()
    zone = serializers.CharField(help_text="State / assigned zone location")
    depot = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    accepted_terms = serializers.BooleanField(default=True)

    def validate_phone_number(self, value):
        value = "".join(value.split())  # designs show "+234 000 0000 000"
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("An account already exists with this phone number.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if Profile.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account already exists with this work email.")
        return value

    def validate_accepted_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        # driver_id doubles as the badge ID and is unique + max_length=10,
        # so "INS-1234" fits. Retry on the (unlikely) collision.
        badge_id = generate_badge_id()
        for _ in range(10):
            if not User.objects.filter(driver_id=badge_id).exists():
                break
            badge_id = generate_badge_id()
        else:
            raise serializers.ValidationError("Could not allocate a badge ID. Please try again.")

        user = User.objects.create_user(
            phone_number=validated_data["phone_number"],
            password=validated_data["password"],
            driver_id=badge_id,
            role="inspector",
        )

        # Every driver-only column on Profile is passed explicitly so this never
        # depends on a model default: license_expiry in particular used to be
        # NOT NULL and blew up inspector signup with an IntegrityError.
        Profile.objects.create(
            user=user,
            full_name=validated_data["full_name"].strip(),
            gender="",
            date_of_birth=None,
            email=validated_data["email"],
            phone_number=user.phone_number,
            medical_history="",
            drivers_license="",
            license_expiry=None,
            emergency_contact_phone_no="",
            depot_zone=validated_data["zone"],
        )

        inspector_profile = InspectorProfile.objects.create(
            user=user,
            badge_id=badge_id,
            zone=validated_data["zone"],
            depot=validated_data.get("depot", ""),
            active_since=timezone.localdate(),
        )
        NotificationPreference.objects.get_or_create(user=user)
        return inspector_profile


class InspectorLoginSerializer(serializers.Serializer):
    """Login with the Inspector Badge ID (or phone number) + password."""

    badge_id = serializers.CharField(help_text="Inspector Badge ID e.g. INS-0521, or phone number")
    password = serializers.CharField(write_only=True)
    zone = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        identifier = attrs["badge_id"].strip().lstrip("#")

        user = (
            User.objects.filter(driver_id__iexact=identifier).first()
            or User.objects.filter(phone_number=identifier).first()
        )
        if user is None:
            raise serializers.ValidationError("No inspector found with that badge ID.")

        user = authenticate(phone_number=user.phone_number, password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Invalid badge ID or password.")
        if user.role != "inspector":
            raise serializers.ValidationError("This account is not an inspector account.")

        attrs["user"] = user
        return attrs


class VerifyAccountSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        user = User.objects.filter(phone_number=attrs["phone_number"]).first()
        if user is None:
            raise serializers.ValidationError("Invalid phone number.")

        otp = OTPCode.objects.filter(user=user, code=attrs["code"], is_used=False).last()
        if otp is None:
            raise serializers.ValidationError("Invalid verification code.")
        if otp.is_expired():
            raise serializers.ValidationError("This code has expired. Request a new one.")

        attrs["user"] = user
        attrs["otp"] = otp
        return attrs


class ResendCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        if not User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("No account found with this phone number.")
        return value


# ─────────────────────────── Shifts ───────────────────────────


class ShiftSerializer(serializers.ModelSerializer):
    inspector_id = serializers.CharField(source="inspector.id", read_only=True)
    window = serializers.SerializerMethodField()

    class Meta:
        model = Shift
        fields = [
            "id", "inspector_id", "label", "depot", "zone", "terminal",
            "role_label", "clearance_level", "date", "start_time", "end_time",
            "window", "status", "started_at", "ended_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "inspector_id", "started_at", "ended_at", "created_at", "updated_at"]

    def get_window(self, obj):
        if not obj.start_time or not obj.end_time:
            return ""
        fmt = "%I:%M%p"
        return f"{obj.start_time.strftime(fmt)} - {obj.end_time.strftime(fmt)}"


# ─────────────────────────── Clearance ───────────────────────────


class ClearanceSerializer(serializers.ModelSerializer):
    """A trip as it appears in the Vehicle Clearance list / Inspection Details."""

    driver_name = serializers.SerializerMethodField()
    driver_id = serializers.CharField(source="driver.driver_id", read_only=True)
    driver_user_id = serializers.CharField(source="driver.id", read_only=True)
    driver_phone = serializers.CharField(source="driver.phone_number", read_only=True)
    clearance_status = serializers.SerializerMethodField()
    volume = serializers.SerializerMethodField()
    inspection = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id", "trip_id", "truck_no", "product_type", "requested_volume",
            "loaded_volume", "volume", "destination", "distance", "date_from",
            "estimated_time_arrival", "seal_number", "sensor_status",
            "driver_name", "driver_id", "driver_user_id", "driver_phone",
            "clearance_status", "inspection", "created_at",
        ]

    def get_driver_name(self, obj):
        profile = Profile.objects.filter(user=obj.driver).first()
        return profile.full_name if profile else obj.driver.phone_number

    def get_clearance_status(self, obj):
        status_obj = getattr(obj, "inspection_status", None)
        return status_obj.inspection_status if status_obj else "pending"

    def get_volume(self, obj):
        litres = obj.loaded_volume or obj.requested_volume or 0
        return f"{obj.product_type} {litres:,} Liters"

    def get_inspection(self, obj):
        inspection = obj.inspections.order_by("-created_at").first()
        if not inspection:
            return None
        return {
            "id": inspection.id,
            "decision": inspection.decision,
            "notes": inspection.notes,
            "photo": inspection.photo,
            "checklist": {
                "valid_documentation": inspection.valid_documentation,
                "tank_seals_intact": inspection.tank_seals_intact,
                "safe_operating_condition": inspection.safe_operating_condition,
                "fire_extinguisher": inspection.fire_extinguisher,
                "license_verified": inspection.license_verified,
            },
            "created_at": inspection.created_at,
        }


class ApproveClearanceSerializer(serializers.Serializer):
    """Safety checklist + notes + photo -> vehicle cleared for dispatch."""

    valid_documentation = serializers.BooleanField(default=False)
    tank_seals_intact = serializers.BooleanField(default=False)
    safe_operating_condition = serializers.BooleanField(default=False)
    fire_extinguisher = serializers.BooleanField(default=False)
    license_verified = serializers.BooleanField(default=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    photo_file = serializers.ImageField(required=False, validators=[validate_is_file], write_only=True)

    def validate(self, attrs):
        checklist = [
            attrs.get("valid_documentation"),
            attrs.get("tank_seals_intact"),
            attrs.get("safe_operating_condition"),
            attrs.get("fire_extinguisher"),
            attrs.get("license_verified"),
        ]
        if not all(checklist):
            raise serializers.ValidationError(
                {"checklist": "Complete all checklist items to clear this vehicle."}
            )
        return attrs


class RejectClearanceSerializer(serializers.Serializer):
    """Reject Vehicle bottom sheet: reason + situation report + photo."""

    REASON_CHOICES = [
        "Documentation issue",
        "Seal tampering",
        "Unsafe vehicle condition",
        "Missing fire extinguisher",
        "Driver certification issue",
        "Volume discrepancy",
        "Other",
    ]

    reason = serializers.CharField()
    situation_report = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    photo_file = serializers.ImageField(required=False, validators=[validate_is_file], write_only=True)


# ─────────────────────────── Alerts ───────────────────────────


class AlertEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertEvent
        fields = ["id", "label", "description", "occurred_at"]


class AlertSerializer(serializers.ModelSerializer):
    driver_name = serializers.SerializerMethodField()
    driver_phone = serializers.CharField(source="driver.phone_number", read_only=True)
    truck_no = serializers.SerializerMethodField()
    trip_id = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    timeline = AlertEventSerializer(many=True, read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "reference", "alert_type", "category", "title", "message",
            "status", "status_label", "location", "latitude", "longitude",
            "photo", "inspector_notes", "driver_name", "driver_phone",
            "truck_no", "trip_id", "timeline", "created_at", "resolved_at",
        ]
        read_only_fields = ["id", "reference", "created_at", "resolved_at"]

    def get_driver_name(self, obj):
        profile = Profile.objects.filter(user=obj.driver).first()
        return profile.full_name if profile else obj.driver.phone_number

    def get_truck_no(self, obj):
        return obj.trip.truck_no if obj.trip else ""

    def get_trip_id(self, obj):
        return obj.trip.trip_id if obj.trip else None

    def get_status_label(self, obj):
        return {
            "received": "Alert received",
            "responding": "Responding",
            "monitoring": "Security monitoring is in progress",
            "help_on_way": "Help on the way",
            "escalated": "Escalated to command centre",
            "resolved": "Alert Resolved",
        }.get(obj.status, obj.status)


class CreateAlertSerializer(serializers.Serializer):
    """Raised from the driver app (SOS / incident report)."""

    trip_id = serializers.CharField(required=False, allow_blank=True)
    alert_type = serializers.ChoiceField(choices=["distress", "incident"], default="distress")
    category = serializers.ChoiceField(
        choices=["spillage", "security", "breakdown", "other"], default="other"
    )
    title = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    location = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    def validate_trip_id(self, value):
        if not value:
            return None
        trip = Trip.objects.filter(trip_id=value).first()
        if trip is None:
            raise serializers.ValidationError(f"Trip with trip_id '{value}' does not exist.")
        return trip


class AlertActionSerializer(serializers.Serializer):
    """Add notes / mark resolved / escalate."""

    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)


# ─────────���───────────────── Queries + notifications ───────────────────────────


class InspectorQuerySerializer(serializers.ModelSerializer):
    trip_id = serializers.SerializerMethodField()
    inspector_name = serializers.SerializerMethodField()

    class Meta:
        model = InspectorQuery
        fields = [
            "id", "trip_id", "inspector_name", "subject", "message",
            "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_trip_id(self, obj):
        return obj.trip.trip_id

    def get_inspector_name(self, obj):
        profile = Profile.objects.filter(user=obj.inspector).first()
        return profile.full_name if profile else obj.inspector.phone_number


class SendQuerySerializer(serializers.Serializer):
    subject = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(max_length=1000)


class AppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppNotification
        fields = [
            "id", "title", "body", "category", "reference",
            "is_read", "is_important", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id", "distress_calls", "loading_events", "dispatch_confirmations",
            "vibration", "email_notifications", "in_app_only",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ─────────────────────────── Helpers used by views ───────────────────────────


def upload_optional_photo(file, folder):
    if not file:
        return None
    url = upload_image(file, folder=folder)
    if not url:
        raise serializers.ValidationError({"photo_file": "Upload failed. Check Cloudinary credentials."})
    return url


def set_clearance_status(trip, value):
    status_obj, _ = InspectionStatus.objects.get_or_create(trip=trip)
    status_obj.inspection_status = value
    status_obj.save()
    return status_obj


__all__ = [
    "Alert", "AlertEvent", "AlertSerializer", "AlertEventSerializer",
    "AlertActionSerializer", "AppNotification", "AppNotificationSerializer",
    "ApproveClearanceSerializer", "ClearanceSerializer", "CreateAlertSerializer",
    "Inspection", "InspectorLoginSerializer", "InspectorProfileSerializer",
    "InspectorQuery", "InspectorQuerySerializer", "InspectorSignupSerializer",
    "NotificationPreference", "NotificationPreferenceSerializer",
    "RejectClearanceSerializer", "Rejection", "ResendCodeSerializer",
    "SendQuerySerializer", "ShiftSerializer", "VerifyAccountSerializer",
    "set_clearance_status", "upload_optional_photo",
]
