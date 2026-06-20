from django.db import models
from uuid import uuid4
from athens.models import User


def generate_id():
    return uuid4().hex


class UserSettings(models.Model):

    THEME_CHOICES = [
        ("light", "light"),
        ("dark", "dark"),
    ]

    LANGUAGE_CHOICES = [
        ("english", "english"),
    ]

    id = models.CharField(max_length=255, primary_key=True, default=generate_id, null=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')

    # Biometric Setup
    use_fingerprint = models.BooleanField(default=False)
    use_face_id = models.BooleanField(default=False)

    # Notifications
    push_notifications = models.BooleanField(default=True)
    trip_notifications = models.BooleanField(default=True)
    sms_messages = models.BooleanField(default=False)
    query_alerts = models.BooleanField(default=True)
    sos_sounds = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=False)
    in_app_only = models.BooleanField(default=False)

    # Language
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='english')

    # Theme
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')

    # Location and GPS
    location_services = models.BooleanField(default=True)

    # Help Center theme
    help_center_theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings for {self.user.phone_number}"
