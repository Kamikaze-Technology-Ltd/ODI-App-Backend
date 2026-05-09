import json
import jwt

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import ChatRoom, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        token = self._get_token_from_scope()
        self.user = await self._get_user_from_token(token)

        if self.user is None:
            await self.close(code=4001)
            return

        if not await self._is_participant(self.user, self.room_id):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            content = json.loads(text_data).get('message', '').strip()
        except (json.JSONDecodeError, AttributeError):
            return

        if not content:
            return

        message = await self._save_message(self.user, self.room_id, content)

        from notifications.services import notify_chat_participants_async
        await notify_chat_participants_async(self.room_id, self.user.id, content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': str(message.id),
                'message': message.content,
                'sender': str(message.sender_id),
                'timestamp': message.timestamp.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp'],
        }))

    # --- Helpers ---

    def _get_token_from_scope(self):
        query_string = self.scope.get('query_string', b'').decode()
        params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
        return params.get('token')

    @database_sync_to_async
    def _get_user_from_token(self, token):
        if not token:
            return None
        try:
            UntypedToken(token)
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return User.objects.filter(id=decoded.get('user_id')).first()
        except (TokenError, Exception):
            return None

    @database_sync_to_async
    def _is_participant(self, user, room_id):
        return ChatRoom.objects.filter(id=room_id, participants=user).exists()

    @database_sync_to_async
    def _save_message(self, user, room_id, content):
        room = ChatRoom.objects.get(id=room_id)
        return Message.objects.create(room=room, sender=user, content=content)
