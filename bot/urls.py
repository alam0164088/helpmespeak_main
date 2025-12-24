from django.urls import path
from .views import ChatView, LanguagesView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat'),
    path('languages/', LanguagesView.as_view(), name='languages'),
]