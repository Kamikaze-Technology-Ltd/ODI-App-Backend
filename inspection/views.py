from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Inspection, Rejection
from .serializers import InspectionSerializer, RejectionSerializer


class InspectionListView(generics.ListAPIView):
    """
    GET /inspections/                       — list all inspections by the requesting inspector
    GET /inspections/?trip_id=<trip_id>     — filter to a specific trip
    """
    serializer_class = InspectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Inspection.objects.filter(inspector=user)
        trip_id = self.request.query_params.get('trip_id')
        if trip_id:
            qs = qs.filter(trip__trip_id=trip_id)
        return qs


class InspectionCreateView(generics.CreateAPIView):
    """POST /inspections/create/   — create a new inspection (inspector role required)"""
    queryset = Inspection.objects.all()
    serializer_class = InspectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class InspectionRetrieveView(generics.RetrieveAPIView):
    """GET /inspections/<id>/   — retrieve an inspection"""
    queryset = Inspection.objects.all()
    serializer_class = InspectionSerializer
    permission_classes = [IsAuthenticated]


class InspectionUpdateView(generics.UpdateAPIView):
    """PATCH/PUT /inspections/update/<id>/   — update an inspection"""
    queryset = Inspection.objects.all()
    serializer_class = InspectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class InspectionDeleteView(generics.DestroyAPIView):
    """DELETE /inspections/delete/<id>/   — delete an inspection"""
    queryset = Inspection.objects.all()
    serializer_class = InspectionSerializer
    permission_classes = [IsAuthenticated]


class RejectionCreateView(generics.CreateAPIView):
    """POST /rejections/create/   — create a rejection for an inspection"""
    queryset = Rejection.objects.all()
    serializer_class = RejectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class RejectionRetrieveView(generics.RetrieveAPIView):
    """GET /rejections/<id>/   — retrieve a rejection"""
    queryset = Rejection.objects.all()
    serializer_class = RejectionSerializer
    permission_classes = [IsAuthenticated]


class RejectionUpdateView(generics.UpdateAPIView):
    """PATCH/PUT /rejections/update/<id>/   — update a rejection"""
    queryset = Rejection.objects.all()
    serializer_class = RejectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


