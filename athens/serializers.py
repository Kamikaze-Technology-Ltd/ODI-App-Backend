from athens.models import User
from rest_framework_simplejwt import serializers as jwt_seriaizer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['phone_number', 'password', 'driver_id', 'id']
        extra_kwargs = {"password" : {"write_only" : True}}
    
    def create(self, validated_data):   
        user = User.objects.create_user(**validated_data)
        return user

class CustomTokenSerializer(TokenObtainPairSerializer):
    username_field = 'phone_number'
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['is_superuser'] = user.is_superuser
        token['is_staff'] = user.is_staff

        return token

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        user = authenticate(
            phone_number=phone_number,
            password=password
        )

        if user is None:
            raise serializers.ValidationError("Invalid phone number or password")

        refresh = self.get_token(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'is_admin': user.is_superuser,
            'is_staff': user.is_staff,
        }