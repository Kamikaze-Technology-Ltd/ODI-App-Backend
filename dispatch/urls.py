from django.urls import path
from .views import (
    TripListView, TripCreateView, TripRetrieveView,
    TripUpdateView, TripDeleteView,
    TripsByStatusView, TripStatusView, InspectorListView,
)


urlpatterns = [
    path('inspector-list/', InspectorListView.as_view(), name='inspector-list'),
    path('trips/', TripListView.as_view(), name='trip-list'),
    path('trips/create/', TripCreateView.as_view(), name='trip-create'),
    path('trips/update/<str:pk>/', TripUpdateView.as_view(), name='trip-update'),
    path('trips/delete/<str:pk>/', TripDeleteView.as_view(), name='trip-delete'),
    path('trips/by-status/', TripsByStatusView.as_view(), name='trips-by-status'),
    path('trips/<str:pk>/', TripRetrieveView.as_view(), name='trip-detail'),
    path('trips/<str:trip_id>/status/', TripStatusView.as_view(), name='trip-status'),
]
