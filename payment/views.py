from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

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
