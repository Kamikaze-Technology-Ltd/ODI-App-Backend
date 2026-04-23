from django.urls import path
from .views import ChatRoomListCreateView, MessageListCreateView, MarkMessagesReadView

urlpatterns = [
    path('rooms/', ChatRoomListCreateView.as_view(), name='chat-rooms'),
    path('messages/', MessageListCreateView.as_view(), name='chat-messages'),
    path('rooms/<str:room_id>/read/', MarkMessagesReadView.as_view(), name='chat-mark-read'),
]
