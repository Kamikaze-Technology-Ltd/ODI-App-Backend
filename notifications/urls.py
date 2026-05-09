from django.urls import path
from .views import RegisterDeviceTokenView, UnregisterDeviceTokenView

urlpatterns = [
    path('register-token/', RegisterDeviceTokenView.as_view(), name='register-token'),
    path('unregister-token/', UnregisterDeviceTokenView.as_view(), name='unregister-token'),
]
