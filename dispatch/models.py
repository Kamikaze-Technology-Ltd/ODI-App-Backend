from django.db import models
from uuid import uuid4
from athens.models import User


def generate_id():
    return uuid4().hex


class Trip(models.Model):

    PRODUCT_TYPE_CHOICES = [
        ("PMS", "PMS"),
    ]
    SENSOR_STATUS_CHOICES = [
        ("verified", "verified"),
        ("unverified", "unverified"),
    ]
    VOLUME_MATCH_CHOICES = [
        ("confirmed", "confirmed"),
        ("unconfirmed", "unconfirmed"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)

    # Seal Docks Info
    sensor_status = models.CharField(max_length=10, null=False, choices=SENSOR_STATUS_CHOICES)
    trip_id = models.CharField(max_length=15, unique=True, null=False)
    product_type = models.CharField(max_length=5, null=False, choices=PRODUCT_TYPE_CHOICES)
    seal_number = models.CharField(max_length=15, null=False)

    # Dispenser Reading Info
    variance = models.IntegerField(null=False, default=0)
    requested_volume = models.IntegerField(null=False, default=0)
    loaded_volume = models.IntegerField(null=False, default=0)
    volume_match = models.CharField(max_length=11, null=False, default='unconfirmed', choices=VOLUME_MATCH_CHOICES)

    # Dispatch Summary
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='driver_trips')
    truck_no = models.CharField(max_length=15, null=False)
    distance = models.CharField(max_length=15, null=False)
    date_from = models.DateTimeField()
    destination = models.CharField(max_length=255, null=False)
    estimated_time_arrival = models.DateTimeField()
    assigned_inspector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inspector_trips')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Other Fields
    tanker = models.CharField(max_length=20, default = 0)

    def __str__(self):
        return f"{self.trip_id} - {self.destination}"
    
class TripStatus(models.Model):

    CURRENT_STATUS_CHOICES = [
        ("started", "started"),
        ("in-transit", "in-transit"),
        ("arrival-pending", "arrival-pending"),
        ("completed", "completed"),
    ]

    QUERY_STATUS_CHOICES = [
        ("on-route", "on-route"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)
    current_status = models.CharField(max_length=255, null=False, choices=CURRENT_STATUS_CHOICES)
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE)
    query_status = models.CharField(max_length=255, choices=QUERY_STATUS_CHOICES, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)