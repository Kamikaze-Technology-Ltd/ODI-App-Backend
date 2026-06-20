from django.db import models
from uuid import uuid4
from athens.models import User
from dispatch.models import Trip

def generate_id():
    return uuid4().hex

# Create your models here.
class Reports(models.Model):

    REASON_STATUS_CHOICES = [
        ("vehicle-breakdown", "vehicle-breakdown"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)
    reason = models.CharField(max_length=255, null=False, choices=REASON_STATUS_CHOICES)
    message = models.TextField()
    photo = models.URLField()
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='reports')


class Feedback(models.Model):
    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback {self.id[:8]} from {self.user}"
