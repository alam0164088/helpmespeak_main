from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import serializers

from .models import Plan, Subscription
from .serializers import (
    PlanSerializer,
    SubscriptionStatusSerializer,
    IAPValidateSerializer
)
from authentication.models import User
from rest_framework.authentication import get_authorization_header
from rest_framework_simplejwt.authentication import JWTAuthentication

# ---------------------------
# Plan List View
# ---------------------------
class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]


# ---------------------------
# Subscription Manage View
# ---------------------------
class SubscriptionManageView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionStatusSerializer

    def get_object(self):
        subscription = get_object_or_404(
            Subscription,
            user=self.request.user
        )
        # Auto-expire check
        subscription.is_active_and_valid()
        return subscription


# ---------------------------
# IAP Validation View
# ---------------------------
class IAPValidateView(views.APIView):
    permission_classes = [IsAuthenticated]  # DRF will ensure user is authenticated via Authorization header

    def post(self, request, *args, **kwargs):
        serializer = IAPValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use .get() to safely access 'token'
        token = serializer.validated_data.get('token')  # Will return None if 'token' is not provided
        platform = serializer.validated_data['platform']
        product_id = serializer.validated_data['product_id']

        print(f"Platform: {platform}, Product ID: {product_id}, Token: {token}")

        # Get User from request.user
        user = request.user
        print(f"Authenticated User: {user}")

        # Get Plan
        if platform == 'apple':
            plan = Plan.objects.filter(apple_product_id=product_id, is_active=True).first()
            print(f"Plan found for Apple: {plan}")
        elif platform == 'google':
            plan = Plan.objects.filter(google_product_id=product_id, is_active=True).first()
            print(f"Plan found for Google: {plan}")
        else:
            return Response(
                {"error": "Invalid platform"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not plan:
            return Response(
                {"detail": "No Plan matches the given query."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get or Create Subscription
        subscription, _ = Subscription.objects.get_or_create(user=user)

        # Activate Paid Plan
        subscription.activate(plan)
        subscription.platform = platform
        subscription.latest_receipt_token = token  # Save the purchase_token for reference (can be None)
        subscription.save()

        # Response
        response_data = {
            "success": True,
            "platform": platform,
            "product_id": product_id,
            "purchase_token": token,
            "subscription": {
                "status": subscription.status,
                "plan": subscription.plan.name,
                "price": str(subscription.plan.price),
                "currency": subscription.plan.currency,
                "interval": subscription.plan.interval,
                "renewal_date": subscription.renewal_date.isoformat() if subscription.renewal_date else None,
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)
    

# hello



class SubscriptionCheckView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            subscription = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return Response({
                "active": False,
                "need_subscription": True,
                "message": "You need a subscription to continue using the service."
            }, status=200)

        # ✅ Auto-check subscription validity        class IAPValidateSerializer(serializers.Serializer):
            token = serializers.CharField(required=False)  # Make token optional
            platform = serializers.ChoiceField(choices=['google', 'apple'], required=True)
            product_id = serializers.CharField(required=True)
        subscription.is_active_and_valid()

        if subscription.status == 'expired':
            return Response({
                "active": False,
                "need_subscription": True,
                "message": "Your free trial has expired. Please subscribe to continue."
            }, status=200)

        # যদি এখনও ট্রায়াল/পেইড একটিভ থাকে
        return Response({
            "active": True,
            "need_subscription": False,
            "status": subscription.status,
            "plan": subscription.plan.name if subscription.plan else None,
            "renewal_date": subscription.renewal_date,
        }, status=200)




# subscription/admin_views.py

from authentication.permissions import IsAdmin
from authentication.models import User



class SubscriptionStatsView(views.APIView):
    """
    Admin API: Shows subscriber/unsubscriber stats with name and email.
    """
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        subscribers = []
        unsubscribers = []

        all_users = User.objects.all()

        for user in all_users:
            try:
                subscription = Subscription.objects.get(user=user)
                subscription.is_active_and_valid()  # auto expiry check

                if subscription.status in ['active', 'trial']:
                    subscribers.append({
                        "name": user.full_name or user.email,
                        "email": user.email,
                        "status": subscription.status,
                        "plan": subscription.plan.name if subscription.plan else None,
                        "renewal_date": subscription.renewal_date
                    })
                else:
                    unsubscribers.append({
                        "name": user.full_name or user.email,
                        "email": user.email,
                        "status": subscription.status
                    })

            except Subscription.DoesNotExist:
                unsubscribers.append({
                    "name": user.full_name or user.email,
                    "email": user.email,
                    "status": "no subscription"
                })

        return Response({
            "total_users": all_users.count(),
            "subscribers_count": len(subscribers),
            "unsubscribers_count": len(unsubscribers),
            "subscribers": subscribers,
            "unsubscribers": unsubscribers
        }, status=200)


class IAPValidateSerializer(serializers.Serializer):
    token = serializers.CharField(required=False)  # Make token optional
    platform = serializers.ChoiceField(choices=['google', 'apple'], required=True)
    product_id = serializers.CharField(required=True)
