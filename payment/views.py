# payment/views.py (IAP specific views)

import requests
import json # JSON Parsing এর জন্য যুক্ত
from datetime import datetime
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils.timezone import make_aware
from rest_framework import generics

# Google Auth Libraries for production (আপনাকে এইগুলো ইনস্টল করতে হবে)
# from google.oauth2 import service_account
# import google.auth.transport.requests

from .models import Plan, Subscription
from .serializers import IAPValidateSerializer, PlanSerializer
# ... (অন্যান্য ইম্পোর্ট যেমন generics, status) ...

APPLE_VERIFY_URL = "https://buy.itunes.apple.com/verifyReceipt"
APPLE_SANDBOX_VERIFY_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
GOOGLE_API_URL = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"


class PlanListView(generics.ListAPIView):
    """GET /api/payment/plans/ - IAP আইডি সহ প্ল্যান লিস্ট ফ্রন্টএন্ডকে প্রদান করে।"""
    # এখন models.py ঠিক থাকায় এটি কাজ করবে
    queryset = Plan.objects.filter(is_active=True).all() 
    serializer_class = PlanSerializer

class IAPValidateView(views.APIView):
    """
    POST /api/payment/iap/validate/
    মোবাইল অ্যাপ থেকে আসা রসিদ/টোকেন যাচাই করে সাবস্ক্রিপশন স্ট্যাটাস আপডেট করে।
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = IAPValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        platform = serializer.validated_data['platform']
        product_id = serializer.validated_data['product_id']

        if platform == 'apple':
            return self._validate_apple_receipt(request.user, token, product_id)
        elif platform == 'google':
            return self._validate_google_token(request.user, token, product_id)
        
        return Response({"error": "Invalid platform specified."}, status=status.HTTP_400_BAD_REQUEST)

    # ... ( _validate_apple_receipt এবং _validate_google_token লজিক অপরিবর্তিত) ...

    # আপনার পূর্বের _validate_apple_receipt এবং _validate_google_token কোড এখানে ব্যবহার করুন

    # নতুন _get_google_access_token লজিক
    def _get_google_access_token(self):
        """
        Google Service Account ব্যবহার করে রানটাইমে অ্যাক্সেস টোকেন তৈরি করে।
        প্রোডাকশনের জন্য এটি আবশ্যক।
        """
        # 🚨 যদি google-auth ইনস্টল না থাকে, তবে একটি টেম্পোরারি ফিক্স ব্যবহার করুন 🚨
        if not hasattr(settings, 'GOOGLE_SERVICE_ACCOUNT_FILE'):
            # যদি সেটিংস কনফিগার করা না থাকে, তবে একটি ডামি টোকেন ফিরিয়ে দিন (ডেভেলপমেন্টের জন্য)
            print("WARNING: GOOGLE_SERVICE_ACCOUNT_FILE not set. Using dummy token.")
            return "DUMMY_GOOGLE_ACCESS_TOKEN" 
        
        # 🚧 প্রোডাকশনের জন্য নিচের লজিকটি কাজে লাগান 🚧
        try:
            # Service Account Key ফাইল থেকে ক্রেডেনশিয়াল লোড
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=['https://www.googleapis.com/auth/androidpublisher']
            )
            
            # টোকেন রিফ্রেশ এবং রিটার্ন
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            return credentials.token
            
        except Exception as e:
            print(f"Google Auth Token Generation Failed: {e}")
            # প্রোডাকশনের সময় এখানে লগিং যোগ করুন
            return None # টোকেন তৈরি ব্যর্থ হলে None রিটার্ন করবে
        
from .serializers import SubscriptionStatusSerializer # এই ইমপোর্টটি নিশ্চিত করুন

class SubscriptionManageView(generics.RetrieveUpdateAPIView):
    """
    GET /api/payment/subscription/manage/ : বর্তমান সাবস্ক্রিপশনের স্ট্যাটাস দেখায়।
    PATCH/PUT /api/payment/subscription/manage/ : সাবস্ক্রিপশন বাতিল বা আপডেট করার জন্য।
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionStatusSerializer

    def get_object(self):
        """
        বর্তমানে লগইন করা ব্যবহারকারীর সাবস্ক্রিপশন অবজেক্টটি ফেরৎ দেবে। 
        যদি সাবস্ক্রিপশন না থাকে, তবে 404 দেবে।
        """
        # ব্যবহারকারীর সাবস্ক্রিপশন টেনে আনুন, না থাকলে 404 দেবে
        return get_object_or_404(Subscription, user=self.request.user)

    def update(self, request, *args, **kwargs):
        # ⚠️ এখানে সাবস্ক্রিপশন বাতিলের কাস্টম লজিক যুক্ত করতে পারেন।
        # যেমন: request.data.get('action') == 'cancel' হলে API কল করে বাতিল করা।
        instance = self.get_object()
        
        # ডামি বাতিল লজিক:
        if request.data.get('action') == 'cancel':
            instance.status = 'cancelled'
            instance.save()
            return Response({"message": "Subscription cancelled successfully."}, status=status.HTTP_200_OK)
            
        return super().update(request, *args, **kwargs)