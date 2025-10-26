# payment/serializers.py

from rest_framework import serializers
from .models import Plan, Subscription

class PlanSerializer(serializers.ModelSerializer):
    """প্ল্যান লিস্ট API এর জন্য ব্যবহৃত হবে।"""
    class Meta:
        model = Plan
        # এখন এই ফিল্ডগুলো models.py তে আছে
        fields = ('id', 'name', 'price', 'currency', 'interval', 'is_active', 'apple_product_id', 'google_product_id') 
        
class IAPValidateSerializer(serializers.Serializer):
    """অ্যাপল/গুগল প্লে রসিদ বা টোকেন যাচাইয়ের জন্য ইনপুট ডেটা।"""
    token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=['apple', 'google'])
    product_id = serializers.CharField(max_length=100)

class SubscriptionStatusSerializer(serializers.ModelSerializer):
    """সাবস্ক্রিপশন স্ট্যাটাস API এর জন্য ব্যবহৃত হবে।"""
    plan_name = serializers.ReadOnlyField(source='plan.name')
    class Meta:
        model = Subscription
        fields = ['status', 'start_date', 'renewal_date', 'plan_name']