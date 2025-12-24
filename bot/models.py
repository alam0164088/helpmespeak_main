from django.db import models
from django.utils import timezone

class TranslationHistory(models.Model):
    user_input = models.TextField()
    parsed_request = models.JSONField()
    translation_result = models.JSONField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Translation at {self.timestamp}: {self.user_input[:50]}..."