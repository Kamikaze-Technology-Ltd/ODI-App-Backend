from django.urls import path
from .views import (
    ReportsListView, ReportsCreateView, ReportsRetrieveView,
    ReportsUpdateView, ReportsDeleteView,
    FeedbackCreateView, FeedbackDeleteView,
)


urlpatterns = [
    path('', ReportsListView.as_view(), name='reports-list'),
    path('create/', ReportsCreateView.as_view(), name='reports-create'),
    path('update/<str:pk>/', ReportsUpdateView.as_view(), name='reports-update'),
    path('delete/<str:pk>/', ReportsDeleteView.as_view(), name='reports-delete'),
    path('feedback/create/', FeedbackCreateView.as_view(), name='feedback-create'),
    path('feedback/delete/<str:pk>/', FeedbackDeleteView.as_view(), name='feedback-delete'),
    path('<str:pk>/', ReportsRetrieveView.as_view(), name='reports-detail'),
]
