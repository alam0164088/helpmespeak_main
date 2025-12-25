from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from .models import Plan, Subscription
from .serializers import (
    PlanSerializer,
    SubscriptionStatusSerializer,
    IAPValidateSerializer
)

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
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = IAPValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        platform = serializer.validated_data['platform']
        product_id = serializer.validated_data['product_id']

        # ---------------------------
        # Get Plan
        # ---------------------------
        if platform == 'apple':
            plan = get_object_or_404(
                Plan,
                apple_product_id=product_id,
                is_active=True
            )
        elif platform == 'google':
            plan = get_object_or_404(
                Plan,
                google_product_id=product_id,
                is_active=True
            )
        else:
            return Response(
                {"error": "Invalid platform"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------
        # Get or Create Subscription
        # ---------------------------
        subscription, _ = Subscription.objects.get_or_create(
            user=request.user
        )

        # ---------------------------
        # Activate Paid Plan
        # ---------------------------
        subscription.activate(plan)
        subscription.platform = platform
        subscription.latest_receipt_token = token
        subscription.save()

        # ---------------------------
        # Response
        # ---------------------------
        return Response({
            "message": "Subscription activated successfully",
            "status": subscription.status,
            "plan": subscription.plan.name,
            "price": str(subscription.plan.price),
            "interval": subscription.plan.interval,
            "renewal_date": subscription.renewal_date,
            "platform": subscription.platform
        }, status=status.HTTP_200_OK)
    

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

        # ✅ Auto-check subscription validity
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
from authentication.models import User, Token



class SubscriptionStatsView(views.APIView):
    """
    Admin API: Shows subscriber/unsubscriber stats with name, email, and access token.
    """
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        subscribers = []
        unsubscribers = []

        all_users = User.objects.all()

        for user in all_users:
            token = Token.objects.filter(user=user, revoked=False).first()
            access_token = token.access_token if token else None

            try:
                subscription = Subscription.objects.get(user=user)
                subscription.is_active_and_valid()  # auto expire check

                if subscription.status in ['active', 'trial']:
                    subscribers.append({
                        "name": user.full_name or user.username,
                        "email": user.email,
                        "status": subscription.status,
                        "plan": subscription.plan.name if subscription.plan else None,
                        "renewal_date": subscription.renewal_date,
                        "access_token": access_token
                    })
                else:
                    unsubscribers.append({
                        "name": user.full_name or user.username,
                        "email": user.email,
                        "status": subscription.status,
                        "access_token": access_token
                    })

            except Subscription.DoesNotExist:
                unsubscribers.append({
                    "name": user.full_name or user.username,
                    "email": user.email,
                    "status": "no subscription",
                    "access_token": access_token
                })

        return Response({
            "total_users": all_users.count(),
            "subscribers_count": len(subscribers),
            "unsubscribers_count": len(unsubscribers),
            "subscribers": subscribers,
            "unsubscribers": unsubscribers
        }, status=200)
