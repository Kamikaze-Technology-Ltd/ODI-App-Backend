from django.urls import path
from .views import (
    QueryResponseListView, QueryResponseCreateView,
    QueryResponseRetrieveView, QueryResponseUpdateView, QueryResponseDeleteView,
)


urlpatterns = [
    path('', QueryResponseListView.as_view(), name='queries-list'),
    path('create/', QueryResponseCreateView.as_view(), name='queries-create'),
    path('update/<str:pk>/', QueryResponseUpdateView.as_view(), name='queries-update'),
    path('delete/<str:pk>/', QueryResponseDeleteView.as_view(), name='queries-delete'),
    path('<str:pk>/', QueryResponseRetrieveView.as_view(), name='queries-detail'),
]
