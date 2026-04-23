from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'role']


class MessageSerializer(serializers.ModelSerializer):
    sender = ParticipantSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'content', 'timestamp', 'is_read']
        read_only_fields = ['id', 'sender', 'timestamp']


class LastMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.CharField(source='sender.id', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'content', 'timestamp', 'is_read']


class ChatRoomSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(child=serializers.CharField(), write_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'is_group', 'participants', 'participant_ids', 'created_at', 'last_message']
        read_only_fields = ['id', 'created_at']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-timestamp').first()
        return LastMessageSerializer(msg).data if msg else None

    def validate_participant_ids(self, value):
        found = User.objects.filter(id__in=value)
        if found.count() != len(value):
            raise serializers.ValidationError("One or more participant IDs are invalid.")
        return value

    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        request_user = self.context['request'].user

        # Reuse existing 1-1 room if it already exists between the same two users
        if not validated_data.get('is_group', False):
            all_ids = set(participant_ids) | {str(request_user.id)}
            if len(all_ids) == 2:
                for room in ChatRoom.objects.filter(is_group=False, participants__id__in=all_ids).distinct():
                    if set(str(p) for p in room.participants.values_list('id', flat=True)) == all_ids:
                        return room

        room = ChatRoom.objects.create(**validated_data)
        participants = list(User.objects.filter(id__in=participant_ids))
        if request_user not in participants:
            participants.append(request_user)
        room.participants.set(participants)
        return room
