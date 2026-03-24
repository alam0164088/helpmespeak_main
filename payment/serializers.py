# payment/serializers.py

from rest_framework import serializers
from .models import Plan, Subscription

class PlanSerializer(serializers.ModelSerializer):
    """প্ল্যান লিস্ট API এর জন্য ব্যবহৃত হবে।"""
    class Meta:
        model = Plan
        # is_active ফিল্ডটি এখানে যুক্ত করা হলো
        fields = ['id', 'name', 'price', 'currency', 'interval', 'is_active', 'apple_product_id', 'google_product_id']

class SubscriptionStatusSerializer(serializers.ModelSerializer):
    """সাবস্ক্রিপশন স্ট্যাটাস API এর জন্য ব্যবহৃত হবে।"""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    
    class Meta:
        model = Subscription
        fields = ['status', 'plan_name', 'renewal_date', 'platform', 'start_date']

class IAPValidateSerializer(serializers.Serializer):
    """অ্যাপল/গুগল প্লে রসিদ বা টোকেন যাচাইয়ের জন্য ইনপুট ডেটা।"""
    platform = serializers.ChoiceField(choices=['apple', 'google'])
    product_id = serializers.CharField(max_length=255)
    token = serializers.CharField(required=False, allow_blank=True) # Receipt token