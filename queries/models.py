from django.db import models
from uuid import uuid4
from dispatch.models import TripStatus

def generate_id():
    return uuid4().hex

# Create your models here.
class QueryResponse(models.Model): 

    CURRENT_STATUS_CHOICES = [
        ("on_route", "on_route"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)
    estimated_time_arrival = models.DateTimeField()
    current_status = models.CharField(max_length=255, null=False, choices=CURRENT_STATUS_CHOICES)
    additional_notes = models.TextField(null=False)
    your_response = models.TextField(null=False)
    photo = models.URLField()
    trip = models.ForeignKey(TripStatus, on_delete=models.CASCADE, related_name='query_responses')
    