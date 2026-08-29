"""Inspector API views.

Mounted at /api/inspector/. Screens map 1:1 onto these endpoints:

  signup/ verify/ resend-code/ login/      -> onboarding + auth
  me/ shift/ shift/start/ shift/end/       -> profile + assigned shift
  dashboard/                               -> main inspector dashboard
  clearance/ clearance/<trip_id>/          -> vehicle clearance list + details
  clearance/<trip_id>/approve|reject/      -> cleared / declined dispatch
  alerts/ alerts/<id>/ ...                 -> distress + incident alerts
  tracking/<trip_id>/ tracking/<trip_id>/query/ -> live operations map
  notifications/ notifications/settings/   -> notification feed + toggles
  support/ about/                          -> help & support, about the app
"""

import logging

from django.conf import settings as django_settings
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import status, views
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from athens.models import OTPCode, Profile
from dispatch.models import Trip, TripStatus
from inspection.models import Inspection, InspectionStatus, Rejection
from queries.models import QueryResponse

from .models import (
    Alert,
    AlertEvent,
    AppNotification,
    InspectorProfile,
    InspectorQuery,
    NotificationPreference,
    Shift,
)
from .serializers import (
    AlertActionSerializer,
    AlertSerializer,
    AppNotificationSerializer,
    ApproveClearanceSerializer,
    ClearanceSerializer,
    CreateAlertSerializer,
    InspectorLoginSerializer,
    InspectorProfileSerializer,
    InspectorQuerySerializer,
    InspectorSignupSerializer,
    NotificationPreferenceSerializer,
    RejectClearanceSerializer,
    ResendCodeSerializer,
    SendQuerySerializer,
    ShiftSerializer,
    VerifyAccountSerializer,
    set_clearance_status,
    upload_optional_photo,
)

logger = logging.getLogger(__name__)


# ─────────────────────────── helpers ───────────────────────────


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    refresh["is_superuser"] = user.is_superuser
    refresh["is_staff"] = user.is_staff
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def _inspector_profile(user):
    profile, _ = InspectorProfile.objects.get_or_create(
        user=user,
        defaults={"active_since": timezone.localdate()},
    )
    return profile


def _send_otp(user):
    """Invalidate old codes, mint a new one and email it. Never blocks signup."""
    OTPCode.objects.filter(user=user, is_used=False).update(is_used=True)
    otp = OTPCode.objects.create(user=user)

    profile = Profile.objects.filter(user=user).first()
    email = profile.email if profile else None
    if not email:
        return otp

    try:
        html_message = render_to_string(
            "otp_email.html",
            {"user_name": profile.full_name.split(" ")[0] if profile.full_name else "Inspector",
             "otp_code": otp.code},
        )
        send_mail(
            subject="Verify your ODI Inspector account",
            message=f"Your ODI verification code is {otp.code}",
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as exc:  # email must never break onboarding
        logger.warning("[inspector] OTP email failed: %s", exc)
    return otp


def notify(user, title, body="", category="general", reference="", important=False):
    """Write one row into the in-app notification feed."""
    if user is None:
        return None
    return AppNotification.objects.create(
        user=user, title=title, body=body, category=category,
        reference=reference, is_important=important,
    )


def _inspector_trips(user):
    return Trip.objects.filter(assigned_inspector=user)


class IsInspector(IsAuthenticated):
    """Authenticated *and* role=inspector."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return getattr(request.user, "role", None) == "inspector"


# ─────────────────────────── onboarding + auth ───────────────────────────


class InspectorSignupView(views.APIView):
    """POST /api/inspector/signup/ — create your Inspector account."""

    permission_classes = [AllowAny]
    serializer_class = InspectorSignupSerializer

    def post(self, request):
        serializer = InspectorSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inspector_profile = serializer.save()
        user = inspector_profile.user

        _send_otp(user)
        notify(
            user,
            "Welcome to ODI Logistics",
            "Your inspector account was created. Verify your email to continue.",
            category="general",
        )

        return Response(
            {
                "msg": "Account created. A 6-digit verification code was sent to your work email.",
                "user_id": user.id,
                "badge_id": inspector_profile.badge_id,
                "phone_number": user.phone_number,
                "requires_verification": True,
            },
            status=status.HTTP_201_CREATED,
        )


class InspectorVerifyView(views.APIView):
    """POST /api/inspector/verify/ — confirm the 6-digit code."""

    permission_classes = [AllowAny]
    serializer_class = VerifyAccountSerializer

    def post(self, request):
        serializer = VerifyAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = serializer.validated_data["otp"]
        user = serializer.validated_data["user"]
        otp.is_used = True
        otp.save()

        profile = _inspector_profile(user)
        profile.is_verified = True
        profile.save()

        tokens = _tokens_for(user)
        return Response(
            {
                "msg": "Account verified successfully.",
                "badge_id": profile.badge_id,
                "has_shift": Shift.objects.filter(inspector=user).exclude(status="ended").exists(),
                **tokens,
            },
            status=status.HTTP_200_OK,
        )


class InspectorResendCodeView(views.APIView):
    """POST /api/inspector/resend-code/ — resend the verification code."""

    permission_classes = [AllowAny]
    serializer_class = ResendCodeSerializer

    def post(self, request):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from athens.models import User

        user = User.objects.get(phone_number=serializer.validated_data["phone_number"])
        _send_otp(user)
        return Response({"msg": "A new code is on its way."}, status=status.HTTP_200_OK)


class InspectorLoginView(views.APIView):
    """POST /api/inspector/login/ — badge ID (or phone) + password."""

    permission_classes = [AllowAny]
    serializer_class = InspectorLoginSerializer

    def post(self, request):
        serializer = InspectorLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        inspector_profile = _inspector_profile(user)

        zone = serializer.validated_data.get("zone")
        if zone and zone != inspector_profile.zone:
            inspector_profile.zone = zone
            inspector_profile.save()

        profile = Profile.objects.filter(user=user).first()
        tokens = _tokens_for(user)

        response = Response(
            {
                **tokens,
                "user_id": user.id,
                "profile_id": profile.id if profile else None,
                "phone_number": user.phone_number,
                "role": user.role,
                "badge_id": inspector_profile.badge_id,
                "username": (profile.full_name.split(" ")[0] if profile and profile.full_name else "Inspector"),
                "full_name": profile.full_name if profile else "",
                "zone": inspector_profile.zone,
                "clearance_level": inspector_profile.clearance_level,
                "is_on_duty": inspector_profile.is_on_duty,
                "has_shift": Shift.objects.filter(inspector=user).exclude(status="ended").exists(),
            },
            status=status.HTTP_200_OK,
        )
        response.set_cookie("access", tokens["access"], samesite="None", secure=True, httponly=True)
        return response


# ─────────────────────────── profile + shift ───────────────────────────


class InspectorMeView(views.APIView):
    """GET/PATCH /api/inspector/me/ — inspector profile + edit profile."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = InspectorProfileSerializer

    def get(self, request):
        profile = _inspector_profile(request.user)
        return Response(InspectorProfileSerializer(profile).data, status=status.HTTP_200_OK)

    def patch(self, request):
        inspector_profile = _inspector_profile(request.user)
        data = request.data

        for field in ("zone", "depot", "rank"):
            if data.get(field):
                setattr(inspector_profile, field, data.get(field))
        if data.get("clearance_level"):
            inspector_profile.clearance_level = int(data.get("clearance_level"))
        inspector_profile.save()

        profile = Profile.objects.filter(user=request.user).first()
        if profile:
            for field in ("full_name", "email", "phone_number"):
                if data.get(field):
                    setattr(profile, field, data.get(field))

            photo = request.FILES.get("profile_picture_file") or request.FILES.get("photo_file")
            url = upload_optional_photo(photo, "profile_pictures")
            if url:
                profile.profile_picture = url
            profile.save()

        return Response(
            InspectorProfileSerializer(inspector_profile).data, status=status.HTTP_200_OK
        )


class InspectorShiftView(views.APIView):
    """GET /api/inspector/shift/ — my assigned shift. POST creates/assigns one."""

    permission_classes = [IsAuthenticated]
    serializer_class = ShiftSerializer

    def get(self, request):
        shift = Shift.objects.filter(inspector=request.user).exclude(status="ended").first()
        if shift is None:
            return Response(
                {"shift": None, "msg": "No shift assigned yet."}, status=status.HTTP_200_OK
            )
        return Response(ShiftSerializer(shift).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift = serializer.save(inspector=request.user)

        inspector_profile = _inspector_profile(request.user)
        inspector_profile.depot = shift.depot or inspector_profile.depot
        inspector_profile.zone = shift.zone or inspector_profile.zone
        inspector_profile.clearance_level = shift.clearance_level or inspector_profile.clearance_level
        inspector_profile.save()

        notify(
            request.user,
            "Shift assigned",
            f"{shift.label} at {shift.depot or shift.zone}",
            category="general",
        )
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


class InspectorShiftStartView(views.APIView):
    """POST /api/inspector/shift/start/ — 'Start My Shift' → inspector goes Active."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        shift = Shift.objects.filter(inspector=request.user).exclude(status="ended").first()
        if shift is None:
            return Response(
                {"msg": "You have no assigned shift to start."}, status=status.HTTP_400_BAD_REQUEST
            )

        shift.status = "active"
        shift.started_at = timezone.now()
        shift.save()

        inspector_profile = _inspector_profile(request.user)
        inspector_profile.is_on_duty = True
        inspector_profile.save()

        return Response(
            {"msg": "Shift started.", "shift": ShiftSerializer(shift).data, "is_on_duty": True},
            status=status.HTTP_200_OK,
        )


class InspectorShiftEndView(views.APIView):
    """POST /api/inspector/shift/end/ — clock out; dashboard drops to Off-Duty."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        shift = Shift.objects.filter(inspector=request.user, status="active").first()
        if shift:
            shift.status = "ended"
            shift.ended_at = timezone.now()
            shift.save()

        inspector_profile = _inspector_profile(request.user)
        inspector_profile.is_on_duty = False
        inspector_profile.save()

        return Response({"msg": "Shift ended.", "is_on_duty": False}, status=status.HTTP_200_OK)


# ─────────────────────────── dashboard ───────────────────────────


class InspectorDashboardView(views.APIView):
    """GET /api/inspector/dashboard/ — everything the home screen renders."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        inspector_profile = _inspector_profile(user)
        shift = Shift.objects.filter(inspector=user).exclude(status="ended").first()

        trips = _inspector_trips(user)
        today = timezone.now().date()

        pending_trips = [
            trip for trip in trips
            if getattr(getattr(trip, "inspection_status", None), "inspection_status", "pending") == "pending"
        ]
        cleared_today = Inspection.objects.filter(
            inspector=user, decision="approved", created_at__date=today
        ).count()
        in_transit = TripStatus.objects.filter(
            trip__assigned_inspector=user, current_status__in=["in-transit", "started"]
        ).count()
        incidents_responded = Alert.objects.filter(
            inspector=user, status__in=["responding", "resolved", "help_on_way", "monitoring"]
        ).count()
        confirmed_deliverables = TripStatus.objects.filter(
            trip__assigned_inspector=user, current_status="completed"
        ).count()

        active_alert = (
            Alert.objects.filter(Q(inspector=user) | Q(inspector__isnull=True))
            .exclude(status="resolved")
            .first()
        )

        return Response(
            {
                "inspector": InspectorProfileSerializer(inspector_profile).data,
                "shift": ShiftSerializer(shift).data if shift else None,
                "is_on_duty": inspector_profile.is_on_duty,
                "zone": inspector_profile.zone,
                "depot": inspector_profile.depot,
                "summary": {
                    "cleared_vehicles": cleared_today,
                    "vehicles_in_transit": in_transit,
                    "incidents_responded": incidents_responded,
                    "confirmed_deliverables": confirmed_deliverables,
                    "pending_clearance": len(pending_trips),
                    "distress_calls": Alert.objects.filter(
                        alert_type="distress", status__in=["received", "responding", "monitoring", "help_on_way"]
                    ).count(),
                    "loading_queue": trips.count(),
                    "unread_notifications": AppNotification.objects.filter(
                        user=user, is_read=False
                    ).count(),
                },
                "pending_clearance": ClearanceSerializer(pending_trips[:10], many=True).data,
                "active_alert": AlertSerializer(active_alert).data if active_alert else None,
            },
            status=status.HTTP_200_OK,
        )


# ─────────────────────────── vehicle clearance ───────────────────────────


class ClearanceListView(views.APIView):
    """GET /api/inspector/clearance/?status=all|pending|declined|cleared"""

    permission_classes = [IsAuthenticated]
    serializer_class = ClearanceSerializer

    def get(self, request):
        wanted = (request.query_params.get("status") or "all").lower()
        trips = _inspector_trips(request.user)

        if wanted != "all":
            trips = [
                trip for trip in trips
                if getattr(getattr(trip, "inspection_status", None), "inspection_status", "pending") == wanted
            ]

        return Response(ClearanceSerializer(trips, many=True).data, status=status.HTTP_200_OK)


class ClearanceDetailView(views.APIView):
    """GET /api/inspector/clearance/<trip_id>/ — inspection details header card."""

    permission_classes = [IsAuthenticated]
    serializer_class = ClearanceSerializer

    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, trip_id=trip_id)
        return Response(ClearanceSerializer(trip).data, status=status.HTTP_200_OK)


class ClearanceApproveView(views.APIView):
    """POST /api/inspector/clearance/<trip_id>/approve/ — clear for dispatch."""

    permission_classes = [IsInspector]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = ApproveClearanceSerializer

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, trip_id=trip_id)
        serializer = ApproveClearanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        photo_url = upload_optional_photo(data.get("photo_file"), "inspection_photos")

        inspection = Inspection.objects.create(
            inspector=request.user,
            trip=trip,
            valid_documentation=data["valid_documentation"],
            tank_seals_intact=data["tank_seals_intact"],
            safe_operating_condition=data["safe_operating_condition"],
            fire_extinguisher=data["fire_extinguisher"],
            license_verified=data["license_verified"],
            notes=data.get("notes", ""),
            photo=photo_url,
            decision="approved",
        )
        set_clearance_status(trip, "cleared")

        inspector_profile = _inspector_profile(request.user)
        inspector_profile.vehicles_cleared += 1
        inspector_profile.save()

        notify(
            trip.driver,
            "Vehicle cleared for dispatch",
            f"{trip.trip_id} — {trip.truck_no} has been approved. You are good to roll.",
            category="clearance",
            reference=trip.trip_id,
            important=True,
        )
        notify(
            request.user,
            "Clearance recorded",
            f"You cleared {trip.truck_no} ({trip.trip_id}).",
            category="clearance",
            reference=trip.trip_id,
        )

        return Response(
            {
                "msg": "Vehicle cleared for dispatch.",
                "inspection_id": inspection.id,
                "clearance_status": "cleared",
                "trip": ClearanceSerializer(trip).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ClearanceRejectView(views.APIView):
    """POST /api/inspector/clearance/<trip_id>/reject/ — declined dispatch."""

    permission_classes = [IsInspector]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = RejectClearanceSerializer

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, trip_id=trip_id)
        serializer = RejectClearanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        photo_url = upload_optional_photo(data.get("photo_file"), "rejection_photos")

        inspection = Inspection.objects.create(
            inspector=request.user,
            trip=trip,
            notes=data.get("situation_report", ""),
            photo=photo_url,
            decision="rejected",
        )
        Rejection.objects.create(
            inspection=inspection,
            reason=data["reason"],
            situation_report=data.get("situation_report", ""),
            photo=photo_url,
        )
        set_clearance_status(trip, "declined")

        notify(
            trip.driver,
            "Dispatch declined",
            f"{trip.trip_id} was declined: {data['reason']}.",
            category="clearance",
            reference=trip.trip_id,
            important=True,
        )

        return Response(
            {
                "msg": "Dispatch declined.",
                "inspection_id": inspection.id,
                "clearance_status": "declined",
                "reason": data["reason"],
                "trip": ClearanceSerializer(trip).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RejectionReasonsView(views.APIView):
    """GET /api/inspector/clearance/reasons/ — options for the reason dropdown."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"reasons": RejectClearanceSerializer.REASON_CHOICES}, status=status.HTTP_200_OK)


class SafetyChecklistView(views.APIView):
    """GET /api/inspector/clearance/checklist/ — the 5 safety checklist items."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "items": [
                    {"key": "valid_documentation", "label": "Valid documentation",
                     "hint": "Waybill, Loading receipt"},
                    {"key": "tank_seals_intact", "label": "Tank seals intact and unbroken", "hint": ""},
                    {"key": "safe_operating_condition", "label": "Vehicle in safe operating condition", "hint": ""},
                    {"key": "fire_extinguisher", "label": "Fire extinguisher present and working well", "hint": ""},
                    {"key": "license_verified", "label": "Driver's license and certification verified", "hint": ""},
                ]
            },
            status=status.HTTP_200_OK,
        )


# ─────────────────────────── alerts ───────────────────────────


class AlertListView(views.APIView):
    """GET /api/inspector/alerts/?type=all|distress|incident — emergency alerts.

    POST creates an alert (used by the driver app SOS button).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AlertSerializer

    def get(self, request):
        wanted = (request.query_params.get("type") or "all").lower()
        user = request.user

        if getattr(user, "role", None) == "inspector":
            alerts = Alert.objects.filter(Q(inspector=user) | Q(inspector__isnull=True))
        else:
            alerts = Alert.objects.filter(driver=user)

        if wanted in ("distress", "incident"):
            alerts = alerts.filter(alert_type=wanted)

        payload = AlertSerializer(alerts, many=True).data
        return Response(
            {
                "results": payload,
                "counts": {
                    "all": alerts.count(),
                    "distress": alerts.filter(alert_type="distress").count(),
                    "incident": alerts.filter(alert_type="incident").count(),
                },
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = CreateAlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        trip = data.get("trip_id")
        alert = Alert.objects.create(
            trip=trip,
            driver=request.user,
            inspector=trip.assigned_inspector if trip else None,
            alert_type=data["alert_type"],
            category=data["category"],
            title=data.get("title", "") or data["category"].title(),
            message=data.get("message", ""),
            location=data.get("location", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )
        AlertEvent.objects.create(alert=alert, label="Alert Received", description="Reported from the driver app")

        if alert.inspector:
            AlertEvent.objects.create(alert=alert, label="Inspector Notified")
            notify(
                alert.inspector,
                f"{alert.get_category_display().title()} alert — {alert.reference}",
                alert.message or "A driver raised a distress call.",
                category="distress",
                reference=alert.reference,
                important=True,
            )

        return Response(AlertSerializer(alert).data, status=status.HTTP_201_CREATED)


class AlertDetailView(views.APIView):
    """GET /api/inspector/alerts/<id>/ — distress alert detail + timeline."""

    permission_classes = [IsAuthenticated]
    serializer_class = AlertSerializer

    def get(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)
        return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)


class AlertRespondView(views.APIView):
    """POST /api/inspector/alerts/<id>/respond/ — 'Respond Now'."""

    permission_classes = [IsInspector]

    def post(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)
        alert.inspector = request.user
        alert.status = "responding"
        alert.save()
        AlertEvent.objects.create(alert=alert, label="Response Unit Dispatched")
        notify(
            alert.driver,
            "An inspector is responding",
            "Help is on the way. Stay with your vehicle if it is safe to do so.",
            category="distress",
            reference=alert.reference,
            important=True,
        )
        return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)


class AlertNotesView(views.APIView):
    """POST /api/inspector/alerts/<id>/notes/ — 'Add Notes'."""

    permission_classes = [IsInspector]
    serializer_class = AlertActionSerializer

    def post(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)
        serializer = AlertActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data.get("notes", "")
        alert.inspector_notes = (f"{alert.inspector_notes}\n{note}").strip() if alert.inspector_notes else note
        alert.save()
        AlertEvent.objects.create(alert=alert, label="Inspector note added", description=note[:255])
        return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)


class AlertResolveView(views.APIView):
    """POST /api/inspector/alerts/<id>/resolve/ — 'Mark as Resolved'."""

    permission_classes = [IsInspector]
    serializer_class = AlertActionSerializer

    def post(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)
        note = request.data.get("notes", "")
        if note:
            alert.inspector_notes = (f"{alert.inspector_notes}\n{note}").strip()
        alert.status = "resolved"
        alert.resolved_at = timezone.now()
        alert.inspector = alert.inspector or request.user
        alert.save()
        AlertEvent.objects.create(alert=alert, label="Incident Resolved", description=note[:255])
        notify(
            alert.driver,
            "Incident resolved",
            f"{alert.reference} has been marked resolved by your inspector.",
            category="distress",
            reference=alert.reference,
        )
        return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)


class AlertEscalateView(views.APIView):
    """POST /api/inspector/alerts/<id>/escalate/ — 'Escalate' to command centre."""

    permission_classes = [IsInspector]

    def post(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)
        alert.status = "escalated"
        alert.inspector = alert.inspector or request.user
        alert.save()
        AlertEvent.objects.create(
            alert=alert, label="Escalated to Command Center",
            description=request.data.get("notes", "")[:255],
        )
        return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)


# ─────────────────────────── live operations map ───────────────────────────


class TripTrackingView(views.APIView):
    """GET /api/inspector/tracking/<trip_id>/ — status, location, ETA."""

    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, trip_id=trip_id)
        trip_status, _ = TripStatus.objects.get_or_create(
            trip=trip, defaults={"current_status": "started"}
        )
        latest_response = (
            QueryResponse.objects.filter(trip=trip_status).order_by("-estimated_time_arrival").first()
        )

        eta = latest_response.estimated_time_arrival if latest_response else trip.estimated_time_arrival
        remaining = None
        if eta:
            delta = eta - timezone.now()
            minutes = max(int(delta.total_seconds() // 60), 0)
            remaining = f"{minutes // 60}hr {minutes % 60}mins" if minutes >= 60 else f"{minutes}mins"

        return Response(
            {
                "trip": ClearanceSerializer(trip).data,
                "current_status": trip_status.current_status,
                "track_status": "ON TRACK" if trip_status.current_status != "arrival-pending" else "ARRIVING",
                "location": trip.destination,
                "eta": eta,
                "eta_label": remaining,
                "queries": InspectorQuerySerializer(
                    InspectorQuery.objects.filter(trip=trip), many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class SendQueryView(views.APIView):
    """POST /api/inspector/tracking/<trip_id>/query/ — 'Send Query' to a driver."""

    permission_classes = [IsInspector]
    serializer_class = SendQuerySerializer

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, trip_id=trip_id)
        serializer = SendQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = InspectorQuery.objects.create(
            trip=trip,
            inspector=request.user,
            driver=trip.driver,
            subject=serializer.validated_data.get("subject", ""),
            message=serializer.validated_data["message"],
        )
        notify(
            trip.driver,
            "New query from your inspector",
            serializer.validated_data["message"],
            category="query",
            reference=trip.trip_id,
            important=True,
        )
        return Response(
            {"msg": "Query sent to driver.", "query": InspectorQuerySerializer(query).data},
            status=status.HTTP_201_CREATED,
        )


class InspectorQueryListView(views.APIView):
    """GET /api/inspector/queries/ — queries I sent (or received, as a driver)."""

    permission_classes = [IsAuthenticated]
    serializer_class = InspectorQuerySerializer

    def get(self, request):
        user = request.user
        queryset = (
            InspectorQuery.objects.filter(inspector=user)
            if getattr(user, "role", None) == "inspector"
            else InspectorQuery.objects.filter(driver=user)
        )
        trip_id = request.query_params.get("trip_id")
        if trip_id:
            queryset = queryset.filter(trip__trip_id=trip_id)
        return Response(InspectorQuerySerializer(queryset, many=True).data, status=status.HTTP_200_OK)


# ─────────────────────────── notifications ───────────────────────────


class NotificationFeedView(views.APIView):
    """GET /api/inspector/notifications/?filter=all|unread|important"""

    permission_classes = [IsAuthenticated]
    serializer_class = AppNotificationSerializer

    def get(self, request):
        wanted = (request.query_params.get("filter") or "all").lower()
        feed = AppNotification.objects.filter(user=request.user)

        if wanted == "unread":
            feed = feed.filter(is_read=False)
        elif wanted == "important":
            feed = feed.filter(is_important=True)

        all_feed = AppNotification.objects.filter(user=request.user)
        return Response(
            {
                "results": AppNotificationSerializer(feed, many=True).data,
                "counts": {
                    "all": all_feed.count(),
                    "unread": all_feed.filter(is_read=False).count(),
                    "important": all_feed.filter(is_important=True).count(),
                },
            },
            status=status.HTTP_200_OK,
        )


class NotificationReadView(views.APIView):
    """POST /api/inspector/notifications/<id>/read/ and .../read-all/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        if pk:
            AppNotification.objects.filter(user=request.user, pk=pk).update(is_read=True)
        else:
            AppNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"msg": "Marked as read."}, status=status.HTTP_200_OK)


class NotificationPreferenceView(views.APIView):
    """GET/PATCH /api/inspector/notifications/settings/ — the toggle list."""

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer

    def get(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(preference).data, status=status.HTTP_200_OK)

    def patch(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────── support + about ───────────────────────────


class SupportView(views.APIView):
    """GET /api/inspector/support/ — Help & Support channels."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "channels": [
                    {"key": "live_chat", "label": "Live Chat",
                     "description": "Chat with the ODI command centre", "value": ""},
                    {"key": "phone", "label": "Phone Call Support",
                     "description": "Speak to a support officer", "value": "+2348038490040"},
                    {"key": "whatsapp", "label": "WhatsApp",
                     "description": "Message us on WhatsApp", "value": "+2348038490040"},
                ]
            },
            status=status.HTTP_200_OK,
        )


class AboutView(views.APIView):
    """GET /api/inspector/about/ — About the App."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "name": "ODI LOGISTICS",
                "tagline": "Powering Every Mile",
                "version": "1.0.0",
                "version_label": "Version 1.0 available",
                "copyright": "© 2024-2026 ODI Logistics. All rights reserved.",
            },
            status=status.HTTP_200_OK,
        )
