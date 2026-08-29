"""Driver-side data that previously only existed as client mock JSON.

Every list the driver app renders now has a real table or a real derived
endpoint behind it: dispense logs, quick replies, report reasons and emergency
contacts. Reference rows (replies / reasons / contacts) auto-seed on first read
so a fresh database still returns the catalogue the screens expect, while an
admin can edit or extend them from Django admin afterwards.
"""

from uuid import uuid4

from django.db import models

from athens.models import User
from dispatch.models import Trip


def generate_id():
    return uuid4().hex


class DispenseLog(models.Model):
    """One dispensing event recorded by the driver at a delivery point."""

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="dispense_logs")
    driver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="dispense_logs", null=True, blank=True
    )

    station = models.CharField(max_length=255, blank=True)
    product_type = models.CharField(max_length=16, blank=True)

    opening_reading = models.IntegerField(default=0)
    closing_reading = models.IntegerField(default=0)
    volume_dispensed = models.IntegerField(default=0)

    notes = models.TextField(blank=True)
    photo = models.URLField(null=True, blank=True)

    dispensed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dispensed_at"]

    def save(self, *args, **kwargs):
        # The app sends either the two meter readings or the volume directly.
        if not self.volume_dispensed and self.closing_reading and self.opening_reading:
            self.volume_dispensed = max(self.closing_reading - self.opening_reading, 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.trip.trip_id} - {self.volume_dispensed}L"


class QuickReply(models.Model):
    """Canned chat replies shown above the keyboard."""

    AUDIENCE_CHOICES = [
        ("driver", "driver"),
        ("inspector", "inspector"),
        ("both", "both"),
    ]

    DEFAULTS = [
        ("On my way to the terminal", "driver", 1),
        ("Loading in progress", "driver", 2),
        ("Arrived at the depot", "driver", 3),
        ("Running late due to traffic", "driver", 4),
        ("Delivery completed", "driver", 5),
        ("Confirm your ETA", "inspector", 6),
        ("Confirm your current location", "inspector", 7),
        ("Report reason for delay", "inspector", 8),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    text = models.CharField(max_length=255, unique=True)
    audience = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default="both")
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "text"]

    def __str__(self):
        return self.text


class ReportReason(models.Model):
    """Options in the 'Report an issue' reason dropdown."""

    DEFAULTS = [
        ("vehicle-breakdown", "Vehicle breakdown", 1),
        ("spillage", "Product spillage", 2),
        ("security-incident", "Security incident", 3),
        ("route-blocked", "Route blocked", 4),
        ("seal-tampering", "Seal tampering", 5),
        ("volume-discrepancy", "Volume discrepancy", 6),
        ("other", "Other", 7),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    key = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "label"]

    def __str__(self):
        return self.label


class EmergencyContact(models.Model):
    """Numbers on the driver emergency screen and the inspector support screen."""

    DEFAULTS = [
        ("control-room", "ODI Control Room", "+2348038490040", "Available 24/7", 1),
        ("fire-service", "Fire Service", "112", "National emergency line", 2),
        ("police", "Police", "112", "National emergency line", 3),
        ("medical", "Medical Response", "112", "Ambulance dispatch", 4),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id)
    key = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    phone_number = models.CharField(max_length=32)
    description = models.CharField(max_length=255, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "label"]

    def __str__(self):
        return f"{self.label} ({self.phone_number})"
