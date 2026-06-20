from rest_framework import serializers
from .models import UserSettings


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
