from django.shortcuts import render
from rest_framework import generics
from .models import Document
from .serializers import DocumentSerializer

# Create your views here.
class DocumentListCreateAPIView(
    generics.ListCreateAPIView):

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer