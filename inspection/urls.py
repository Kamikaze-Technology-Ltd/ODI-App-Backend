from django.urls import path
from .views import (
    InspectionListView, InspectionCreateView, InspectionRetrieveView,
    InspectionUpdateView, InspectionDeleteView,
    RejectionCreateView, RejectionRetrieveView, RejectionUpdateView,
)


urlpatterns = [
    path('', InspectionListView.as_view(), name='inspection-list'),
    path('create/', InspectionCreateView.as_view(), name='inspection-create'),
    path('update/<str:pk>/', InspectionUpdateView.as_view(), name='inspection-update'),
    path('delete/<str:pk>/', InspectionDeleteView.as_view(), name='inspection-delete'),
    path('rejections/create/', RejectionCreateView.as_view(), name='rejection-create'),
    path('rejections/update/<str:pk>/', RejectionUpdateView.as_view(), name='rejection-update'),
    path('rejections/<str:pk>/', RejectionRetrieveView.as_view(), name='rejection-detail'),
    path('<str:pk>/', InspectionRetrieveView.as_view(), name='inspection-detail'),
]
