import os
import firebase_admin
from firebase_admin import credentials, messaging
from exponent_server_sdk import PushClient, PushMessage
from channels.db import database_sync_to_async


def _init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
        })
        firebase_admin.initialize_app(cred)


def _send_expo(token, title, body, data):
    try:
        PushClient().publish(
            PushMessage(to=token, title=title, body=body, data=data, sound="default")
        )
    except Exception:
        pass


def _send_fcm(token, title, body, data):
    try:
        _init_firebase()
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in data.items()},
            token=token,
        )
        messaging.send(message)
    except Exception:
        pass


def send_push_notification(token, title, body, data=None):
    if not token:
        return
    payload = data or {}
    if token.startswith("ExponentPushToken"):
        _send_expo(token, title, body, payload)
    else:
        _send_fcm(token, title, body, payload)


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
