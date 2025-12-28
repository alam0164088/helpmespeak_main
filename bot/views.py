from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    SmartTranslationRequestSerializer,
    TranslationResponseSerializer,
    SupportedLanguagesSerializer
)
from .translator import AITranslatorChatbot
from .models import TranslationHistory
import re

class ChatView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self.translator = AITranslatorChatbot()
            self.error = None
        except ValueError as e:
            self.translator = None
            self.error = str(e)

    def post(self, request):
        if not self.translator:
            return Response({"error": self.error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = SmartTranslationRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_input = serializer.validated_data['input']
            parsed_request = self.translator.parse_with_ai(user_input)

            # Ensure translation only proceeds when user explicitly specified a target language
            if parsed_request.get('is_translation_request', False):
                explicit_marker = bool(
                    re.search(r'\b(?:to|in|into)\s+[A-Za-z]+', user_input, flags=re.IGNORECASE)
                    or any(kw in user_input.lower() for kw in ['translate', 'অনুবাদ', 'traduire', 'ترجم', 'how do you say'])
                )
                if not explicit_marker:
                    # Treat as normal chat if no explicit target language/keyword present
                    reply = self.translator.get_normal_reply(user_input)
                    # Build translation-style JSON where translated_text holds the chat reply.
                    source_code = self.translator.detect_language(user_input) or 'auto'
                    source_name = self.translator.supported_languages.get(source_code, 'Unknown') if source_code != 'auto' else 'Unknown'
                    json_output = self.translator.create_json_output(
                        original_text=user_input,
                        translated_text=reply,
                        source_language=source_name,
                        target_language=None,
                        source_code=source_code,
                        target_code=None,
                        success=True,
                        error=None
                    )
                    return Response(json_output, status=status.HTTP_200_OK)

            # 🔹 Translation request
            if parsed_request.get('is_translation_request', False):
                text = parsed_request.get('text')
                target_code = parsed_request.get('target_language_code')
                target_name = parsed_request.get('target_language_name')
                if not text or not target_code:
                    return Response({"error": "Could not parse text or target language"}, status=status.HTTP_400_BAD_REQUEST)

                result = self.translator.process_translation(text, target_code, target_name)
                response_serializer = TranslationResponseSerializer(data=result)
                if response_serializer.is_valid():
                    TranslationHistory.objects.create(
                        user_input=user_input,
                        parsed_request=parsed_request,
                        translation_result=result
                    )
                    return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
                return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 🔹 Normal chat (no translation intent)
            else:
                reply = self.translator.get_normal_reply(user_input)
                source_code = self.translator.detect_language(user_input) or 'auto'
                source_name = self.translator.supported_languages.get(source_code, 'Unknown') if source_code != 'auto' else 'Unknown'
                json_output = self.translator.create_json_output(
                    original_text=user_input,
                    translated_text=reply,
                    source_language=source_name,
                    target_language=None,
                    source_code=source_code,
                    target_code=None,
                    success=True,
                    error=None
                )
                return Response(json_output, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LanguagesView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self.translator = AITranslatorChatbot()
            self.error = None
        except ValueError as e:
            self.translator = None
            self.error = str(e)

    def get(self, request):
        if not self.translator:
            return Response({"error": self.error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        languages = self.translator.get_supported_languages()
        serializer = SupportedLanguagesSerializer(languages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
