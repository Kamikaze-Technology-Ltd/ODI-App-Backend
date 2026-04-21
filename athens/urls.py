from django.urls import path
from .views import CreateUserView, CustomTokenObtainView, ForgotPasswordView, ProfileDetailView, ResetPasswordView, VerifyOTPView, VerifyToken

urlpatterns = [
    path("create/user/", CreateUserView.as_view(), name="Register User"), 
    path("login/user/", CustomTokenObtainView.as_view(), name = "Login user"), 
    path("verify/user/", VerifyToken.as_view(), name = "Login user"), 
    
path("profiles/<str:pk>/", ProfileDetailView.as_view(), name="profile-detail"),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
]