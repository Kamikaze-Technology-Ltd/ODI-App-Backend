from django.urls import path,  include
from .views import CreateUserView, CustomTokenObtainView, ForgotPasswordView, ProfileCreateView, ProfileDetailView, ResetPasswordView, VerifyOTPView, VerifyToken

urlpatterns = [
    path("create/user/", CreateUserView.as_view(), name="Register User"), 
    path("login/user/", CustomTokenObtainView.as_view(), name = "Login user"), 
    path("verify/user/", VerifyToken.as_view(), name = "Login user"), 
    
    path("create/profiles/", ProfileCreateView.as_view(), name="profile-create"),
    path("profiles/<str:pk>/", ProfileDetailView.as_view(), name="profile-detail"),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
]