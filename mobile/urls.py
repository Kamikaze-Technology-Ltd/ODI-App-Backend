from django.urls import path

from .views import (
    ActivityFeedView,
    DispenseLogDetailView,
    DispenseLogView,
    EmergencyContactView,
    QuickReplyView,
    ReportReasonView,
)

urlpatterns = [
    path('dispense-logs/', DispenseLogView.as_view(), name='dispense-logs'),
    path('dispense-logs/<str:pk>/', DispenseLogDetailView.as_view(), name='dispense-log-detail'),
    path('quick-replies/', QuickReplyView.as_view(), name='quick-replies'),
    path('report-reasons/', ReportReasonView.as_view(), name='report-reasons'),
    path('emergency-contacts/', EmergencyContactView.as_view(), name='emergency-contacts'),
    path('activity/', ActivityFeedView.as_view(), name='activity-feed'),
]
