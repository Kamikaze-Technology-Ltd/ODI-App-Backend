from rest_framework import generics, views, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Max
from django.shortcuts import get_object_or_404

from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer


class MessagePagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100


class ChatRoomListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ChatRoom.objects
            .filter(participants=self.request.user)
            .prefetch_related('participants', 'messages__sender')
            .annotate(last_activity=Max('messages__timestamp'))
            .order_by('-last_activity')
        )


class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        room_id = self.request.query_params.get('room_id')
        if not room_id:
            return Message.objects.none()
        room = get_object_or_404(ChatRoom, id=room_id, participants=self.request.user)
        return Message.objects.filter(room=room).select_related('sender').order_by('timestamp')

    def perform_create(self, serializer):
        room_id = self.request.data.get('room')
        room = get_object_or_404(ChatRoom, id=room_id, participants=self.request.user)
        serializer.save(sender=self.request.user, room=room)


class MarkMessagesReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        Message.objects.filter(room=room, is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response({'msg': 'Messages marked as read.'}, status=status.HTTP_200_OK)
