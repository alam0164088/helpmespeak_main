# payment/models.py
from django.db import models
from django.conf import settings 

class Plan(models.Model):
    PLAN_CHOICES = [
        ('monthly', 'Pro Monthly'),
        ('annual', 'Pro Annual'),
    ]
    
    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True, default='monthly')
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
    interval = models.CharField(max_length=10, default='month') 
    is_active = models.BooleanField(default=True)
    
    apple_product_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    google_product_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.price} {self.currency}/{self.interval}"

class Subscription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'), ('active', 'Active'), ('cancelled', 'Cancelled'), 
        ('expired', 'Expired'), ('trial', 'Trialing'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)  # ← Plan, না SubscriptionPlan!
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(auto_now_add=True)
    renewal_date = models.DateTimeField(null=True, blank=True)
    
    latest_receipt_token = models.CharField(max_length=512, null=True, blank=True)
    platform = models.CharField(max_length=10, null=True, blank=True)
    
    def is_active_pro(self):
        return self.status == 'active'

    def __str__(self):
        return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'} ({self.status})"
    


# 