import logging
from athens.models import Profile, User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.core.files.uploadedfile import UploadedFile
from .models import OTPCode
from .utils import upload_image

logger = logging.getLogger(__name__)


def validate_is_file(value):
    if not isinstance(value, UploadedFile):
        raise serializers.ValidationError("A valid file must be uploaded. Plain text is not accepted.")
    return value


class ProfileSerializer(serializers.ModelSerializer):
    profile_picture_file = serializers.ImageField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload profile picture (jpg/png)"
    )
    drivers_license_doc_file = serializers.FileField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload driver's license document (pdf/jpg/png)"
    )
    nin_doc_file = serializers.FileField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload NIN document (pdf/jpg/png)"
    )

    profile_picture = serializers.URLField(read_only=True, required=False)
    drivers_license_doc = serializers.URLField(read_only=True, required=False)
    nin_doc = serializers.URLField(read_only=True, required=False)

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
        read_only_fields = ["id"]

    def _handle_uploads(self, validated_data):
        profile_picture_file = validated_data.pop("profile_picture_file", None)
        drivers_license_file = validated_data.pop("drivers_license_doc_file", None)
        nin_file = validated_data.pop("nin_doc_file", None)

        logger.info(f"[_handle_uploads] profile_picture_file={profile_picture_file} | "
                    f"drivers_license_file={drivers_license_file} | nin_file={nin_file}")

        try:
            if profile_picture_file:
                url = upload_image(profile_picture_file, folder="profile_pictures")
                if not url:
                    raise serializers.ValidationError({"profile_picture_file": "Upload failed. Check Cloudinary credentials."})
                validated_data["profile_picture"] = url

            if drivers_license_file:
                url = upload_image(drivers_license_file, folder="licenses")
                if not url:
                    raise serializers.ValidationError({"drivers_license_doc_file": "Upload failed. Check Cloudinary credentials."})
                validated_data["drivers_license_doc"] = url

            if nin_file:
                url = upload_image(nin_file, folder="nin_docs")
                if not url:
                    raise serializers.ValidationError({"nin_doc_file": "Upload failed. Check Cloudinary credentials."})
                validated_data["nin_doc"] = url

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"[_handle_uploads] Unexpected error: {str(e)}")
            raise serializers.ValidationError({"upload_error": f"File upload failed: {str(e)}"})

        return validated_data

    def create(self, validated_data):
        validated_data = self._handle_uploads(validated_data)
        user = self.context["request"].user
        return Profile.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        validated_data = self._handle_uploads(validated_data)
        # Manually set URL fields since they are read_only and excluded from super().update()
        for field in ("profile_picture", "drivers_license_doc", "nin_doc"):
            if field in validated_data:
                setattr(instance, field, validated_data.pop(field))
        instance.save()
        return super().update(instance, validated_data)


_PROFILE_FIELDS = [
    'full_name', 'gender', 'date_of_birth', 'email', 'medical_history',
    'depot_zone', 'drivers_license', 'license_expiry', 'emergency_contact_phone_no',
    'profile_picture_file', 'drivers_license_doc_file', 'nin_doc_file',
]

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True)
    gender = serializers.ChoiceField(choices=["male", "female"], write_only=True)
    date_of_birth = serializers.DateField(write_only=True)
    email = serializers.EmailField(write_only=True)
    medical_history = serializers.CharField(write_only=True, required=False, allow_blank=True)
    depot_zone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    drivers_license = serializers.CharField(write_only=True, required=False, allow_blank=True)
    license_expiry = serializers.DateField(write_only=True, required=False, allow_null=True)
    emergency_contact_phone_no = serializers.CharField(write_only=True)
    profile_picture_file = serializers.ImageField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload profile picture (jpg/png)"
    )
    drivers_license_doc_file = serializers.FileField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload driver's license document (pdf/jpg/png)"
    )
    nin_doc_file = serializers.FileField(
        write_only=True, required=False,
        validators=[validate_is_file],
        help_text="Upload NIN document (pdf/jpg/png)"
    )

    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'password', 'driver_id', 'role',
            *_PROFILE_FIELDS,
        ]
        extra_kwargs = {"password": {"write_only": True}}
        read_only_fields = ["id"]

    def create(self, validated_data):
        profile_data = {f: validated_data.pop(f) for f in _PROFILE_FIELDS if f in validated_data}
        user = User.objects.create_user(**validated_data)
        profile_data = ProfileSerializer()._handle_uploads(profile_data)
        Profile.objects.create(user=user, phone_number=user.phone_number, **profile_data)
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
