# tts_app/urls.py
from django.urls import path
from .views import TranslateAndTTSAPIView


urlpatterns = [
    path("translatetts", TranslateAndTTSAPIView.as_view(), name="translate-tts"),  # slash optional
    path("translatetts/", TranslateAndTTSAPIView.as_view()),  # slash version
]

