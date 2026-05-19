from django.db.models import Q
from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from athens.models import Profile
from .models import Trip, TripStatus
from .serializers import TripSerializer, TripStatusSerializer, InspectorSerializer


class TripListView(generics.ListAPIView):
    """GET /trips/   — list trips where the requesting user is the driver or assigned inspector"""
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Trip.objects.filter(Q(driver=user) | Q(assigned_inspector=user))


class TripCreateView(generics.CreateAPIView):
    """POST /trips/create/   — create a new trip"""
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]


class TripRetrieveView(generics.RetrieveAPIView):
    """GET /trips/<id>/   — retrieve a trip"""
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]


class TripUpdateView(generics.UpdateAPIView):
    """PATCH/PUT /trips/update/<id>/   — update a trip"""
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]


class TripDeleteView(generics.DestroyAPIView):
    """DELETE /trips/delete/<id>/   — delete a trip"""
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]


class InspectorListView(generics.ListAPIView):
    """
    GET /inspector-list/?full_name=<query>   — list inspectors whose full_name matches the query
    Returns: full_name, profile_picture, user_id
    """
    serializer_class = InspectorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        full_name = self.request.query_params.get('full_name', '')
        return Profile.objects.filter(
            user__role='inspector',
            full_name__icontains=full_name,
        )


class TripsByStatusView(generics.ListAPIView):
    """
    GET /trips/by-status/                   — list all trips (no filter)
    GET /trips/by-status/?status=started    — filter by status
    Valid statuses: started, in_transit, arrival_pending, delivery_complete
    """
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        status_param = self.request.query_params.get('status')
        if not status_param:
            return Trip.objects.all()
        trip_ids = TripStatus.objects.filter(
            current_status=status_param
        ).values_list('trip_id', flat=True)
        return Trip.objects.filter(id__in=trip_ids)


class TripStatusView(views.APIView):
    """
    GET   /trips/<trip_id>/status/   — get the current status of a trip
    PATCH /trips/<trip_id>/status/   — update the status of a trip
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TripStatusSerializer

    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, pk=trip_id)
        trip_status, _ = TripStatus.objects.get_or_create(
            trip=trip,
            defaults={'current_status': 'started'},
        )
        serializer = TripStatusSerializer(trip_status)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, trip_id):
        trip = get_object_or_404(Trip, pk=trip_id)
        trip_status, _ = TripStatus.objects.get_or_create(
            trip=trip,
            defaults={'current_status': 'started'},
        )
        serializer = TripStatusSerializer(trip_status, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
