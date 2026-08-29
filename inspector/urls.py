from django.urls import path

from .views import (
    AboutView,
    AlertDetailView,
    AlertEscalateView,
    AlertListView,
    AlertNotesView,
    AlertResolveView,
    AlertRespondView,
    ClearanceApproveView,
    ClearanceDetailView,
    ClearanceListView,
    ClearanceRejectView,
    InspectorDashboardView,
    InspectorLoginView,
    InspectorMeView,
    InspectorQueryListView,
    InspectorResendCodeView,
    InspectorShiftEndView,
    InspectorShiftStartView,
    InspectorShiftView,
    InspectorSignupView,
    InspectorVerifyView,
    NotificationFeedView,
    NotificationPreferenceView,
    NotificationReadView,
    RejectionReasonsView,
    SafetyChecklistView,
    SendQueryView,
    SupportView,
    TripTrackingView,
)

urlpatterns = [
    # Onboarding + auth
    path('signup/', InspectorSignupView.as_view(), name='inspector-signup'),
    path('verify/', InspectorVerifyView.as_view(), name='inspector-verify'),
    path('resend-code/', InspectorResendCodeView.as_view(), name='inspector-resend-code'),
    path('login/', InspectorLoginView.as_view(), name='inspector-login'),

    # Profile + shift
    path('me/', InspectorMeView.as_view(), name='inspector-me'),
    path('shift/', InspectorShiftView.as_view(), name='inspector-shift'),
    path('shift/start/', InspectorShiftStartView.as_view(), name='inspector-shift-start'),
    path('shift/end/', InspectorShiftEndView.as_view(), name='inspector-shift-end'),

    # Dashboard
    path('dashboard/', InspectorDashboardView.as_view(), name='inspector-dashboard'),

    # Vehicle clearance
    path('clearance/', ClearanceListView.as_view(), name='inspector-clearance-list'),
    path('clearance/checklist/', SafetyChecklistView.as_view(), name='inspector-checklist'),
    path('clearance/reasons/', RejectionReasonsView.as_view(), name='inspector-reject-reasons'),
    path('clearance/<str:trip_id>/', ClearanceDetailView.as_view(), name='inspector-clearance-detail'),
    path('clearance/<str:trip_id>/approve/', ClearanceApproveView.as_view(), name='inspector-clearance-approve'),
    path('clearance/<str:trip_id>/reject/', ClearanceRejectView.as_view(), name='inspector-clearance-reject'),

    # Alerts
    path('alerts/', AlertListView.as_view(), name='inspector-alerts'),
    path('alerts/<str:pk>/', AlertDetailView.as_view(), name='inspector-alert-detail'),
    path('alerts/<str:pk>/respond/', AlertRespondView.as_view(), name='inspector-alert-respond'),
    path('alerts/<str:pk>/notes/', AlertNotesView.as_view(), name='inspector-alert-notes'),
    path('alerts/<str:pk>/resolve/', AlertResolveView.as_view(), name='inspector-alert-resolve'),
    path('alerts/<str:pk>/escalate/', AlertEscalateView.as_view(), name='inspector-alert-escalate'),

    # Live operations map
    path('tracking/<str:trip_id>/', TripTrackingView.as_view(), name='inspector-tracking'),
    path('tracking/<str:trip_id>/query/', SendQueryView.as_view(), name='inspector-send-query'),
    path('queries/', InspectorQueryListView.as_view(), name='inspector-queries'),

    # Notifications
    path('notifications/', NotificationFeedView.as_view(), name='inspector-notifications'),
    path('notifications/settings/', NotificationPreferenceView.as_view(), name='inspector-notification-settings'),
    path('notifications/read-all/', NotificationReadView.as_view(), name='inspector-notifications-read-all'),
    path('notifications/<str:pk>/read/', NotificationReadView.as_view(), name='inspector-notification-read'),

    # Misc
    path('support/', SupportView.as_view(), name='inspector-support'),
    path('about/', AboutView.as_view(), name='inspector-about'),
]
