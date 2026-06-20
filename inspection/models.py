from django.db import models
from uuid import uuid4
from athens.models import User
from dispatch.models import Trip


def generate_id():
    return uuid4().hex


class Inspection(models.Model):

    DECISION_CHOICES = [
        ("approved", "approved"),
        ("rejected", "rejected"),
        ("pending", "pending"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)

    inspector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inspections')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='inspections')

    # Safety checklist
    valid_documentation = models.BooleanField(default=False)
    tank_seals_intact = models.BooleanField(default=False)
    safe_operating_condition = models.BooleanField(default=False)
    fire_extinguisher = models.BooleanField(default=False)
    license_verified = models.BooleanField(default=False)

    # Inspector input
    notes = models.TextField(blank=True)
    photo = models.URLField(null=True, blank=True)

    # Final decision
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Inspection {self.id[:8]} - Trip {self.trip.trip_id} - {self.decision}"


class InspectionStatus(models.Model):

    STATUS_CHOICES = [
        ("pending", "pending"),
        ("declined", "declined"),
        ("cleared", "cleared"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='inspection_status')
    inspection_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"InspectionStatus {self.trip.trip_id} - {self.inspection_status}"


class Rejection(models.Model):

    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)
    inspection = models.OneToOneField(Inspection, on_delete=models.CASCADE, related_name='rejection')
    reason = models.CharField(max_length=255, null=False)
    situation_report = models.TextField(blank=True)
    photo = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rejection {self.id[:8]} - Inspection {self.inspection.id[:8]}"
