from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import DeviceToken
from .serializers import DeviceTokenSerializer


class RegisterDeviceTokenView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceTokenSerializer

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']
        platform = serializer.validated_data.get('platform', '')

        DeviceToken.objects.update_or_create(
            token=token,
            defaults={'user': request.user, 'platform': platform},
        )
        return Response({'msg': 'Token registered.'}, status=status.HTTP_200_OK)


class UnregisterDeviceTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'msg': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        DeviceToken.objects.filter(user=request.user, token=token).delete()
        return Response({'msg': 'Token removed.'}, status=status.HTTP_200_OK)
