from django.urls import path,  include
from .views import CreateUserView, CustomTokenObtainView, ProfileCreateView, ProfileDetailView, VerifyToken

urlpatterns = [
    path("create/user/", CreateUserView.as_view(), name="Register User"), 
    path("login/user/", CustomTokenObtainView.as_view(), name = "Login user"), 
    path("verify/user/", VerifyToken.as_view(), name = "Login user"), 
    
    path("create/profiles/", ProfileCreateView.as_view(), name="profile-create"),
    path("profiles/<str:pk>/", ProfileDetailView.as_view(), name="profile-detail"),
]