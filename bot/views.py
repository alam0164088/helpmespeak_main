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
            return Response(
                {"error": self.error}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serializer = SmartTranslationRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_input = serializer.validated_data['input']
            parsed_request = self.translator.parse_with_ai(user_input)

            if not parsed_request.get('is_translation_request', False):
                return Response(
                    {"error": "Not a valid translation request"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            text = parsed_request.get('text')
            target_code = parsed_request.get('target_language_code')
            target_name = parsed_request.get('target_language_name')

            if not text or not target_code:
                return Response(
                    {"error": "Could not parse text or target language"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            result = self.translator.process_translation(text, target_code, target_name)
            response_serializer = TranslationResponseSerializer(data=result)

            if response_serializer.is_valid():
                # Save history
                TranslationHistory.objects.create(
                    user_input=user_input,
                    parsed_request=parsed_request,
                    translation_result=result
                )
                return Response(
                    response_serializer.validated_data, 
                    status=status.HTTP_200_OK
                )

            return Response(
                response_serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"error": self.error}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        languages = self.translator.get_supported_languages()
        serializer = SupportedLanguagesSerializer(languages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
