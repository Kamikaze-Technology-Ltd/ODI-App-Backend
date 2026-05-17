from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError

from .models import QueryResponse
from .serializers import QueryResponseSerializer


class QueryResponseListView(generics.ListAPIView):
    """GET /queries/?trip_id=<trip_id>   — list query responses for a given trip"""
    serializer_class = QueryResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trip_id = self.request.query_params.get('trip_id')
        if not trip_id:
            raise ValidationError({'trip_id': 'This query parameter is required.'})
        return QueryResponse.objects.filter(trip__trip__trip_id=trip_id)


class QueryResponseCreateView(generics.CreateAPIView):
    """POST /queries/create/   — create a new query response (supports photo upload)"""
    queryset = QueryResponse.objects.all()
    serializer_class = QueryResponseSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class QueryResponseRetrieveView(generics.RetrieveAPIView):
    """GET /queries/<id>/   — retrieve a query response"""
    queryset = QueryResponse.objects.all()
    serializer_class = QueryResponseSerializer
    permission_classes = [IsAuthenticated]


class QueryResponseUpdateView(generics.UpdateAPIView):
    """PATCH/PUT /queries/update/<id>/   — update a query response"""
    queryset = QueryResponse.objects.all()
    serializer_class = QueryResponseSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class QueryResponseDeleteView(generics.DestroyAPIView):
    """DELETE /queries/delete/<id>/   — delete a query response"""
    queryset = QueryResponse.objects.all()
    serializer_class = QueryResponseSerializer
    permission_classes = [IsAuthenticated]
