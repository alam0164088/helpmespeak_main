# bot/serializers.py

from rest_framework import serializers
from .models import TranslationHistory

class SmartTranslationRequestSerializer(serializers.Serializer):
    input = serializers.CharField(max_length=30000, required=True)

class TranslationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    timestamp = serializers.DateTimeField()
    translation = serializers.DictField()
    error = serializers.CharField(allow_null=True)

class SupportedLanguagesSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()