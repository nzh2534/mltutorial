from django.urls import path

from . import views

urlpatterns = [
    path('create/', views.DocumentListCreateAPIView.as_view(), name='document-list'),
]