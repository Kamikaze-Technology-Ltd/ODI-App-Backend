from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UserSettings
from .serializers import UserSettingsSerializer


class UserSettingsView(views.APIView):
    """
    GET   /settings/   — get current user's settings (auto-creates with defaults if missing)
    PATCH /settings/   — update one or more settings fields
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSettingsSerializer

    def get(self, request):
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(settings_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(settings_obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
