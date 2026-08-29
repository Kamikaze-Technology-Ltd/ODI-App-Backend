from django.contrib import admin

from .models import (
    Alert,
    AlertEvent,
    AppNotification,
    InspectorProfile,
    InspectorQuery,
    NotificationPreference,
    Shift,
)


@admin.register(InspectorProfile)
class InspectorProfileAdmin(admin.ModelAdmin):
    list_display = ("badge_id", "user", "rank", "zone", "depot", "clearance_level", "is_on_duty", "vehicles_cleared")
    list_filter = ("rank", "is_on_duty", "is_verified", "zone")
    search_fields = ("badge_id", "zone", "depot", "user__phone_number")


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("inspector", "label", "date", "start_time", "end_time", "depot", "zone", "status")
    list_filter = ("status", "date", "zone")
    search_fields = ("depot", "zone", "terminal")


class AlertEventInline(admin.TabularInline):
    model = AlertEvent
    extra = 0


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("reference", "alert_type", "category", "driver", "inspector", "status", "created_at")
    list_filter = ("alert_type", "category", "status")
    search_fields = ("reference", "location", "message")
    inlines = [AlertEventInline]


@admin.register(InspectorQuery)
class InspectorQueryAdmin(admin.ModelAdmin):
    list_display = ("trip", "inspector", "driver", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("subject", "message")


@admin.register(AppNotification)
class AppNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "is_read", "is_important", "created_at")
    list_filter = ("category", "is_read", "is_important")
    search_fields = ("title", "body", "reference")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "distress_calls", "loading_events", "dispatch_confirmations", "email_notifications")
