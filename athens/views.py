from django.shortcuts import render

from athens.utils import generate_reset_token
from .serializers import ProfileSerializer, UserSerializer, CustomTokenSerializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt import views
from rest_framework import generics
from rest_framework import views
from rest_framework_simplejwt import views as jwt_view
from rest_framework import status 
from .models import OTPCode, Profile, User
import jwt
from django.conf import settings
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import TokenError
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from .serializers import ResetPasswordSerializer, VerifyOTPSerializer, ForgotPasswordSerializer
from django.core.mail import send_mail
from django.template.loader import render_to_string

# Create your views here.

class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class CustomTokenObtainView(jwt_view.TokenObtainPairView):
    serializer_class = CustomTokenSerializer

    def post(self, request: views.Request, *args, **kwargs) -> views.Response:

        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        request_data = request.data
        user = User.objects.get(phone_number = request_data['phone_number'])

        response = Response({
            'is_admin' : data['is_admin'], 
            'is_staff' : data['is_staff'], 
            'access' : data['access'], 
            'user_id' : user.id, 
            'phone_number' : user.phone_number, 
            'driver_id' : user.driver_id, 
            'role' : user.role, 
            'profile_id' : user.profile.id
        })

        response.set_cookie('access', data['access'], samesite='None', secure=True, httponly=True)

        return response

class VerifyToken(views.APIView):

    def get(self, request: views.Request, *args, **kwargs) -> Response:
        try:
            token = request.COOKIES.get('access')
            if not token:
                return Response({'msg' : "Unauthorised"}, status=status.HTTP_401_UNAUTHORIZED)
            UntypedToken(token)


            decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            # decoded_data = TokenBackend(algorithm='HS256')
            # decoded_data = decoded_data.decode(token, verify=True)
            user = User.objects.filter(id = decoded_data["user_id"]).first
            if not user:
                return Response({'msg' : "Unauthorised"}, status=status.HTTP_401_UNAUTHORIZED)

            response = {
                'is_admin' : decoded_data['is_superuser'], 
                'is_staff' : decoded_data['is_staff']
            }

            return Response(response, status=status.HTTP_200_OK)
        except TokenError:
            return Response({'msg' : "Unauthorised"}, status=status.HTTP_401_UNAUTHORIZED)
        
        
class ProfileDetailView(views.APIView):
    """
    GET    /profiles/<id>/   — retrieve profile
    PATCH  /profiles/<id>/   — partial update (only send fields you want to change)
    """
    def get_object(self, pk):
        return get_object_or_404(Profile, pk=pk)

    def get(self, request, pk):
        profile = self.get_object(pk)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        profile = self.get_object(pk)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
####

class ForgotPasswordView(views.APIView):
    """
    POST /auth/forgot-password/
    Accepts phone number, looks up profile email, sends OTP
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']
        user = User.objects.get(phone_number=phone_number)

        # Get email from profile
        profile = Profile.objects.filter(user=user).first()
        if not profile or not profile.email:
            return Response(
                {'msg': 'No email address associated with this account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Invalidate old unused OTPs for this user
        OTPCode.objects.filter(user=user, is_used=False).update(is_used=True)

        # Create new OTP
        otp = OTPCode.objects.create(user=user)
        
        # Send email
        html_message = render_to_string('otp_email.html', {
            'user_name': user.first_name,
            'otp_code': otp.code,
        })

        send_mail(
            subject='Account Verification',
            message=f'Your OTP code is {otp}',  # plain text fallback
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.profile.email],
            html_message=html_message,
            fail_silently=False,
        )

        return Response(
            {'msg': 'OTP sent to your registered email address.'},
            status=status.HTTP_200_OK
        )


class VerifyOTPView(views.APIView):
    """
    POST /auth/verify-otp/
    Accepts phone number + OTP, returns a reset token
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        otp = serializer.validated_data['otp']

        # Generate and attach reset token
        otp.reset_token = generate_reset_token()
        otp.save()

        return Response(
            {'reset_token': otp.reset_token},
            status=status.HTTP_200_OK
        )


class ResetPasswordView(views.APIView):
    """
    POST /auth/reset-password/
    Accepts reset token + new password, updates password
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reset_token = serializer.validated_data['reset_token']
        new_password = serializer.validated_data['new_password']

        otp = OTPCode.objects.filter(reset_token=reset_token, is_used=False).last()
        user = otp.user
        user.set_password(new_password)
        user.save()

        # Mark OTP as used so token can't be reused
        otp.is_used = True
        otp.save()

        return Response(
            {'msg': 'Password reset successful.'},
            status=status.HTTP_200_OK
        )