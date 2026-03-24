from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db.models import Count, Q

from .models import Plan, Subscription
from .serializers import (
    PlanSerializer,
    SubscriptionStatusSerializer,
    IAPValidateSerializer
)
from authentication.permissions import IsAdmin

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
        subscription, created = Subscription.objects.get_or_create(user=self.request.user)
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
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data.get('token')
        platform = serializer.validated_data['platform']
        product_id = serializer.validated_data['product_id']

        # Find the plan
        plan = None
        if platform == 'apple':
            plan = Plan.objects.filter(apple_product_id=product_id, is_active=True).first()
        elif platform == 'google':
            plan = Plan.objects.filter(google_product_id=product_id, is_active=True).first()
        
        if not plan:
            return Response(
                {"error": f"Plan not found for product_id: {product_id} on {platform}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update Subscription
        subscription, _ = Subscription.objects.get_or_create(user=request.user)
        
        # Save receipt token if provided
        if token:
           subscription.latest_receipt_token = token
        
        # Activate Plan (This uses the updated logic in models.py)
        subscription.activate(plan, platform=platform)

        return Response({
            "success": True,
            "platform": platform,
            "product_id": product_id,
            "subscription": {
                "status": subscription.status,
                "plan": subscription.plan.name,
                "renewal_date": subscription.renewal_date
            }
        }, status=status.HTTP_200_OK)


# ---------------------------
# Subscription Check View
# ---------------------------
class SubscriptionCheckView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        subscription, created = Subscription.objects.get_or_create(user=request.user)
        
        is_valid = subscription.is_active_and_valid()
        
        # Determine strict status
        active_status = False
        message = "You need a subscription."
        
        if is_valid:
            active_status = True
            message = "Subscription is active."
        else:
            if subscription.status == 'expired':
                message = "Your subscription has expired."
            elif subscription.status == 'pending':
                message = "No active subscription found."

        return Response({
            "active": active_status,
            "need_subscription": not active_status,
            "status": subscription.status,
            "plan": subscription.plan.name if subscription.plan else "None",
            "renewal_date": subscription.renewal_date,
            "message": message
        }, status=200)


# ---------------------------
# Admin Stats View (Optimized)
# ---------------------------
class SubscriptionStatsView(views.APIView):
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        # Optimized query using database aggregation
        total_subs = Subscription.objects.count()
        
        # Count statuses
        stats = Subscription.objects.aggregate(
            active=Count('id', filter=Q(status='active')),
            trial=Count('id', filter=Q(status='trial')),
            expired=Count('id', filter=Q(status='expired')),
            cancelled=Count('id', filter=Q(status='cancelled')),
        )

        return Response({
            "total_subscriptions": total_subs,
            "breakdown": stats
        }, status=200)
