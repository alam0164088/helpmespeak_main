# payment/urls.py

from django.urls import path
from .views import PlanListView, IAPValidateView, SubscriptionManageView,SubscriptionCheckView

urlpatterns = [
    # প্ল্যান দেখানোর জন্য
    path('plans/', PlanListView.as_view(), name='plan-list'),
    
    path('subscription/manage/', SubscriptionManageView.as_view(), name='subscription-manage'),
    
    path('iap/validate/', IAPValidateView.as_view(), name='iap-validate'), 
    path('check-subscription/', SubscriptionCheckView.as_view(), name='check-subscription'),
]