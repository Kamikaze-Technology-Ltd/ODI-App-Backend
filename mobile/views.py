"""Driver-side endpoints, mounted at /api/mobile/.

These replace the last client-side mock modules in the mobile app:

  dispense-logs/       -> trips > dispense log screen
  quick-replies/       -> chat quick reply chips
  report-reasons/      -> report an issue reason dropdown
  emergency-contacts/  -> driver emergency screen + inspector support
  activity/            -> home screen recent activity feed (derived, not stored)

The catalogue endpoints seed their defaults on first read so a fresh database
still answers with real rows instead of an empty list.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dispatch.models import Trip, TripStatus
from inspection.models import Inspection
from inspector.models import Alert, AppNotification

from .models import DispenseLog, EmergencyContact, QuickReply, ReportReason
from .serializers import (
    CreateDispenseLogSerializer,
    DispenseLogSerializer,
    EmergencyContactSerializer,
    QuickReplySerializer,
    ReportReasonSerializer,
)

logger = logging.getLogger(__name__)


def _seed(model, rows, build):
    """Create the default catalogue rows once, then leave them to the admin."""
    if model.objects.exists():
        return
    for row in rows:
        try:
            model.objects.get_or_create(**build(row))
        except Exception as exc:  # a bad default must never 500 a read
            logger.warning("[mobile] could not seed %s: %s", model.__name__, exc)


class DispenseLogView(views.APIView):
    """GET/POST /api/mobile/dispense-logs/?trip_id=ODI-1023"""

    permission_classes = [IsAuthenticated]
    serializer_class = DispenseLogSerializer

    def get(self, request):
        logs = DispenseLog.objects.all()

        trip_id = request.query_params.get("trip_id")
        if trip_id:
            logs = logs.filter(trip__trip_id=trip_id)

        # Drivers only ever see their own runs; inspectors see the trips
        # assigned to them.
        if getattr(request.user, "role", None) == "inspector":
            logs = logs.filter(trip__assigned_inspector=request.user)
        else:
            logs = logs.filter(trip__driver=request.user)

        data = DispenseLogSerializer(logs, many=True).data
        return Response(
            {
                "results": data,
                "total_dispensed": sum(log.volume_dispensed for log in logs),
                "count": len(data),
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = CreateDispenseLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        trip = data.pop("trip_id")

        log = DispenseLog.objects.create(trip=trip, driver=request.user, **data)
        return Response(DispenseLogSerializer(log).data, status=status.HTTP_201_CREATED)


class DispenseLogDetailView(views.APIView):
    """GET /api/mobile/dispense-logs/<id>/"""

    permission_classes = [IsAuthenticated]
    serializer_class = DispenseLogSerializer

    def get(self, request, pk):
        log = get_object_or_404(DispenseLog, pk=pk)
        return Response(DispenseLogSerializer(log).data, status=status.HTTP_200_OK)


class QuickReplyView(views.APIView):
    """GET /api/mobile/quick-replies/?audience=driver|inspector"""

    permission_classes = [IsAuthenticated]
    serializer_class = QuickReplySerializer

    def get(self, request):
        _seed(
            QuickReply,
            QuickReply.DEFAULTS,
            lambda row: {"text": row[0], "audience": row[1], "position": row[2]},
        )

        audience = request.query_params.get("audience") or getattr(request.user, "role", "driver")
        replies = QuickReply.objects.filter(is_active=True).filter(
            audience__in=[audience, "both"]
        )
        return Response(
            {"results": QuickReplySerializer(replies, many=True).data},
            status=status.HTTP_200_OK,
        )


class ReportReasonView(views.APIView):
    """GET /api/mobile/report-reasons/"""

    permission_classes = [IsAuthenticated]
    serializer_class = ReportReasonSerializer

    def get(self, request):
        _seed(
            ReportReason,
            ReportReason.DEFAULTS,
            lambda row: {"key": row[0], "label": row[1], "position": row[2]},
        )
        reasons = ReportReason.objects.filter(is_active=True)
        return Response(
            {"results": ReportReasonSerializer(reasons, many=True).data},
            status=status.HTTP_200_OK,
        )


class EmergencyContactView(views.APIView):
    """GET /api/mobile/emergency-contacts/"""

    permission_classes = [IsAuthenticated]
    serializer_class = EmergencyContactSerializer

    def get(self, request):
        _seed(
            EmergencyContact,
            EmergencyContact.DEFAULTS,
            lambda row: {
                "key": row[0],
                "label": row[1],
                "phone_number": row[2],
                "description": row[3],
                "position": row[4],
            },
        )
        contacts = EmergencyContact.objects.filter(is_active=True)
        return Response(
            {"results": EmergencyContactSerializer(contacts, many=True).data},
            status=status.HTTP_200_OK,
        )


class ActivityFeedView(views.APIView):
    """GET /api/mobile/activity/ — recent activity, derived from real records.

    Nothing is stored for this screen: the feed is assembled from the user's
    own trips, inspections, alerts and notifications so it can never drift out
    of sync with the data it summarises.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        is_inspector = getattr(user, "role", None) == "inspector"
        events = []

        trips = (
            Trip.objects.filter(assigned_inspector=user)
            if is_inspector
            else Trip.objects.filter(driver=user)
        )

        for trip in trips[:20]:
            events.append(
                {
                    "type": "trip",
                    "title": f"Trip {trip.trip_id}",
                    "description": f"{trip.truck_no} to {trip.destination}",
                    "reference": trip.trip_id,
                    "occurred_at": trip.created_at,
                }
            )

        for trip_status in TripStatus.objects.filter(trip__in=trips)[:20]:
            events.append(
                {
                    "type": "trip_status",
                    "title": trip_status.current_status.replace("-", " ").title(),
                    "description": f"Trip {trip_status.trip.trip_id}",
                    "reference": trip_status.trip.trip_id,
                    "occurred_at": trip_status.updated_at,
                }
            )

        inspections = (
            Inspection.objects.filter(inspector=user)
            if is_inspector
            else Inspection.objects.filter(trip__driver=user)
        )
        for inspection in inspections[:20]:
            events.append(
                {
                    "type": "inspection",
                    "title": f"Inspection {inspection.decision}",
                    "description": f"Trip {inspection.trip.trip_id}",
                    "reference": inspection.trip.trip_id,
                    "occurred_at": inspection.created_at,
                }
            )

        alerts = (
            Alert.objects.filter(inspector=user)
            if is_inspector
            else Alert.objects.filter(driver=user)
        )
        for alert in alerts[:20]:
            events.append(
                {
                    "type": "alert",
                    "title": alert.title or alert.get_category_display(),
                    "description": alert.message,
                    "reference": alert.reference,
                    "occurred_at": alert.created_at,
                }
            )

        for note in AppNotification.objects.filter(user=user)[:20]:
            events.append(
                {
                    "type": "notification",
                    "title": note.title,
                    "description": note.body,
                    "reference": note.reference,
                    "occurred_at": note.created_at,
                }
            )

        events = [e for e in events if e["occurred_at"] is not None]
        events.sort(key=lambda e: e["occurred_at"], reverse=True)

        return Response({"results": events[:30], "count": len(events[:30])}, status=status.HTTP_200_OK)
