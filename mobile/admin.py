from django.contrib import admin

from .models import DispenseLog, EmergencyContact, QuickReply, ReportReason


@admin.register(DispenseLog)
class DispenseLogAdmin(admin.ModelAdmin):
    list_display = ('trip', 'driver', 'station', 'volume_dispensed', 'dispensed_at')
    search_fields = ('trip__trip_id', 'station')
    list_filter = ('product_type',)


@admin.register(QuickReply)
class QuickReplyAdmin(admin.ModelAdmin):
    list_display = ('text', 'audience', 'position', 'is_active')
    list_filter = ('audience', 'is_active')


@admin.register(ReportReason)
class ReportReasonAdmin(admin.ModelAdmin):
    list_display = ('label', 'key', 'position', 'is_active')
    list_filter = ('is_active',)


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ('label', 'phone_number', 'position', 'is_active')
    list_filter = ('is_active',)
