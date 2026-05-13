import logging
import os
from exponent_server_sdk import PushClient, PushMessage
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


def _send_expo(token, title, body, data):
    try:
        access_token = os.getenv("EXPO_ACCESS_TOKEN")
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else None
        ticket = PushClient(session=None, headers=headers).publish(
            PushMessage(to=token, title=title, body=body, data=data, sound="default")
        )
        logger.info(f"[PUSH SENT] to={token[:30]}... title={title!r} body={body!r} ticket={ticket}")
    except Exception as e:
        logger.exception(f"[PUSH FAILED] to={token[:30]}... error={e}")


def send_push_notification(token, title, body, data=None):
    if not token:
        return
    _send_expo(token, title, body, data or {})


def notify_chat_participants(room, sender, content):
    """Synchronous — call from REST views."""
    from notifications.models import DeviceToken

    tokens = DeviceToken.objects.filter(
        user__in=room.participants.exclude(id=sender.id)
    ).values_list('token', flat=True)

    for token in tokens:
        send_push_notification(
            token=token,
            title="New message",
            body=content,
            data={'room_id': str(room.id)},
        )


@database_sync_to_async
def notify_chat_participants_async(room_id, sender_id, content):
    """Async-safe — call from WebSocket consumers."""
    from notifications.models import DeviceToken
    from chat.models import ChatRoom

    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return

    tokens = DeviceToken.objects.filter(
        user__in=room.participants.exclude(id=sender_id)
    ).values_list('token', flat=True)

    for token in tokens:
        send_push_notification(
            token=token,
            title="New message",
            body=content,
            data={'room_id': str(room_id)},
        )
