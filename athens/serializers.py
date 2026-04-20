from athens.models import Profile, User
from rest_framework_simplejwt import serializers as jwt_seriaizer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import OTPCode

from .utils import upload_image


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['phone_number', 'password', 'driver_id', 'id', 'role']
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
        

class ProfileSerializer(serializers.ModelSerializer):
    profile_picture_file = serializers.ImageField(write_only=True, required=False)
    drivers_license_doc_file = serializers.ImageField(write_only=True, required=False)
    nin_doc_file = serializers.ImageField(write_only=True, required=False)
    
    profile_picture = serializers.URLField(read_only=True)
    drivers_license_doc_file = serializers.FileField(write_only=True, required=False)   # change to FileField
    nin_doc_file = serializers.FileField(write_only=True, required=False) 
    
    class Meta:
        model = Profile
        fields = [
            "id", "full_name", "gender", "date_of_birth", "email",
            "medical_history", "phone_number", "depot_zone",
            "drivers_license", "license_expiry", "emergency_contact_phone_no",
            "profile_picture", "profile_picture_file",
            "drivers_license_doc", "drivers_license_doc_file",
            "nin_doc", "nin_doc_file",
        ]

    def _handle_uploads(self, validated_data):
        profile_picture_file = validated_data.pop("profile_picture_file", None)
        drivers_license_file = validated_data.pop("drivers_license_doc_file", None)
        nin_file = validated_data.pop("nin_doc_file", None)

        if profile_picture_file:
            validated_data["profile_picture"] = upload_image(profile_picture_file, folder="profile_pictures")
        if drivers_license_file:
            validated_data["drivers_license_doc"] = upload_image(drivers_license_file, folder="licenses")
        if nin_file:
            validated_data["nin_doc"] = upload_image(nin_file, folder="nin_docs")

        return validated_data

    def create(self, validated_data):
        validated_data = self._handle_uploads(validated_data)
        user = self.context["request"].user
        return Profile.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        validated_data = self._handle_uploads(validated_data)
        return super().update(instance, validated_data)

####
class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        if not User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("No account found with this phone number.")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            user = User.objects.get(phone_number=data['phone_number'])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid phone number.")

        otp = OTPCode.objects.filter(
            user=user,
            code=data['code'],
            is_used=False
        ).last()

        if not otp:
            raise serializers.ValidationError("Invalid OTP code.")

        if otp.is_expired():
            raise serializers.ValidationError("OTP has expired. Please request a new one.")

        data['otp'] = otp
        data['user'] = user
        return data


class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_reset_token(self, value):
        otp = OTPCode.objects.filter(reset_token=value, is_used=False).last()
        if not otp:
            raise serializers.ValidationError("Invalid or already used reset token.")
        if otp.is_expired():
            raise serializers.ValidationError("Reset token has expired.")
        return value
