"""Inspector domain models.

The driver side of ODI already lives in `athens` (users/profiles), `dispatch`
(trips), `inspection` (checklists + rejections), `queries`, `report` and
`notifications`. This app adds everything the Inspector app needs that had no
home yet: inspector identity (badge), shifts, distress/incident alerts with a
response timeline, inspector -> driver queries, and an in-app notification feed
with per-inspector preferences.
"""

import random
from uuid import uuid4

from django.db import models
from django.utils import timezone

from athens.models import User
from dispatch.models import Trip


def generate_id():
    return uuid4().hex


def generate_badge_id():
    """INS-0521 style badge shown on the inspector login screen."""
    return f"INS-{random.randint(1000, 9999)}"


def generate_alert_reference():
    """ODI-1023 style reference shown on the distress alert detail screen."""
    return f"ODI-{random.randint(1000, 9999)}"


class InspectorProfile(models.Model):
    """Work identity for a user whose role is `inspector`."""

    RANK_CHOICES = [
        ("inspector", "Inspector"),
        ("senior_inspector", "Senior Inspector"),
        ("lead_inspector", "Lead Inspector"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="inspector_profile")

    badge_id = models.CharField(max_length=20, unique=True, default=generate_badge_id)
    rank = models.CharField(max_length=32, choices=RANK_CHOICES, default="inspector")

    zone = models.CharField(max_length=255, blank=True)
    depot = models.CharField(max_length=255, blank=True)
    clearance_level = models.PositiveIntegerField(default=1)

    vehicles_cleared = models.PositiveIntegerField(default=0)
    is_on_duty = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    active_since = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.badge_id} ({self.user.phone_number})"


class Shift(models.Model):
    """A shift assignment: depot, zone, window and clearance level."""

    STATUS_CHOICES = [
        ("assigned", "assigned"),
        ("active", "active"),
        ("ended", "ended"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shifts")

    label = models.CharField(max_length=64, default="Morning Shift")
    depot = models.CharField(max_length=255, blank=True)
    zone = models.CharField(max_length=255, blank=True)
    terminal = models.CharField(max_length=255, blank=True)
    role_label = models.CharField(max_length=128, default="Inspector - Clearance & Response")
    clearance_level = models.PositiveIntegerField(default=1)

    date = models.DateField(default=timezone.localdate)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="assigned")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.label} - {self.depot} ({self.status})"


class Alert(models.Model):
    """Distress call or incident report raised from the driver app."""

    ALERT_TYPE_CHOICES = [
        ("distress", "distress"),
        ("incident", "incident"),
    ]

    CATEGORY_CHOICES = [
        ("spillage", "spillage"),
        ("security", "security"),
        ("breakdown", "breakdown"),
        ("other", "other"),
    ]

    STATUS_CHOICES = [
        ("received", "received"),
        ("responding", "responding"),
        ("monitoring", "monitoring"),
        ("help_on_way", "help_on_way"),
        ("escalated", "escalated"),
        ("resolved", "resolved"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    reference = models.CharField(max_length=20, unique=True, default=generate_alert_reference)

    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts")
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="raised_alerts")
    inspector = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_alerts"
    )

    alert_type = models.CharField(max_length=10, choices=ALERT_TYPE_CHOICES, default="distress")
    category = models.CharField(max_length=12, choices=CATEGORY_CHOICES, default="other")
    title = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="received")

    location = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    photo = models.URLField(null=True, blank=True)
    inspector_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} - {self.category} ({self.status})"


class AlertEvent(models.Model):
    """One row of the response timeline on the alert detail screen."""

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name="timeline")
    label = models.CharField(max_length=128)
    description = models.CharField(max_length=255, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["occurred_at"]

    def __str__(self):
        return f"{self.alert.reference} - {self.label}"


class InspectorQuery(models.Model):
    """A query the inspector sends to a driver from the live operations map.

    The driver replies with `queries.QueryResponse`, which the inspector app
    reads back through the trip.
    """

    STATUS_CHOICES = [
        ("sent", "sent"),
        ("acknowledged", "acknowledged"),
        ("answered", "answered"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="inspector_queries")
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_queries")
    driver = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="received_queries"
    )

    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=14, choices=STATUS_CHOICES, default="sent")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Query {self.id[:8]} - {self.trip.trip_id}"


class AppNotification(models.Model):
    """In-app notification feed (All / Unread / Important tabs)."""

    CATEGORY_CHOICES = [
        ("general", "general"),
        ("command_center", "command_center"),
        ("dispatch", "dispatch"),
        ("distress", "distress"),
        ("loading", "loading"),
        ("clearance", "clearance"),
        ("query", "query"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="app_notifications")

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")

    reference = models.CharField(max_length=64, blank=True)
    is_read = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.user.phone_number}"


class NotificationPreference(models.Model):
    """Toggles on the Notification Settings screen."""

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preference")

    distress_calls = models.BooleanField(default=True)
    loading_events = models.BooleanField(default=True)
    dispatch_confirmations = models.BooleanField(default=True)
    vibration = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=False)
    in_app_only = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.user.phone_number}"
