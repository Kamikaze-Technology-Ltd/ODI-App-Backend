from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError

from .models import Reports, Feedback
from .serializers import ReportsSerializer, FeedbackSerializer


class ReportsListView(generics.ListAPIView):
    """GET /reports/?trip_id=<trip_id>   — list reports for a given trip"""
    serializer_class = ReportsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trip_id = self.request.query_params.get('trip_id')
        if not trip_id:
            raise ValidationError({'trip_id': 'This query parameter is required.'})
        return Reports.objects.filter(trip__trip_id=trip_id)


class ReportsCreateView(generics.CreateAPIView):
    """POST /reports/create/   — create a new report (supports photo upload)"""
    queryset = Reports.objects.all()
    serializer_class = ReportsSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class ReportsRetrieveView(generics.RetrieveAPIView):
    """GET /reports/<id>/   — retrieve a report"""
    queryset = Reports.objects.all()
    serializer_class = ReportsSerializer
    permission_classes = [IsAuthenticated]


class ReportsUpdateView(generics.UpdateAPIView):
    """PATCH/PUT /reports/update/<id>/   — update a report"""
    queryset = Reports.objects.all()
    serializer_class = ReportsSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class ReportsDeleteView(generics.DestroyAPIView):
    """DELETE /reports/delete/<id>/   — delete a report"""
    queryset = Reports.objects.all()
    serializer_class = ReportsSerializer
    permission_classes = [IsAuthenticated]


class FeedbackCreateView(generics.CreateAPIView):
    """POST /feedback/create/   — submit feedback"""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]


class FeedbackDeleteView(generics.DestroyAPIView):
    """DELETE /feedback/delete/<id>/   — delete a feedback entry"""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
