from django.db import models
from django.conf import settings
from django.utils.timezone import now
from datetime import timedelta

# Trial period constant
TRIAL_PERIOD_DAYS = 7

# ---------------------------
# Plan Model
# ---------------------------
class Plan(models.Model):
    PLAN_CHOICES = [
        ('trial', 'Free Trial'),
        ('monthly', 'Pro Monthly'),
        ('annual', 'Pro Annual'),
    ]
    
    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
    interval = models.CharField(max_length=10, default='month')  # trial/month/year
    duration_days = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    
    apple_product_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    google_product_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.price} {self.currency}/{self.interval}"


# ---------------------------
# Subscription Model
# ---------------------------
class Subscription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'), 
        ('active', 'Active'), 
        ('cancelled', 'Cancelled'), 
        ('expired', 'Expired'), 
        ('trial', 'Trialing'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(auto_now_add=True)
    renewal_date = models.DateTimeField(null=True, blank=True)
    latest_receipt_token = models.TextField(null=True, blank=True) # Changed to TextField for long tokens
    platform = models.CharField(max_length=20, null=True, blank=True) # apple/google
    
    # ---------------------------
    # Activate Subscription
    # ---------------------------
    def activate(self, plan=None, platform=None):
        """
        Activate subscription with support for Platform switching.
        """
        if plan:
            self.plan = plan

        # Update platform if provided (important for cross-platform support)
        if platform:
            self.platform = platform

        # 1. Determine Duration
        duration_days = TRIAL_PERIOD_DAYS # Default fallback
        
        if self.plan:
            if self.plan.duration_days > 0:
                duration_days = self.plan.duration_days
            else:
                # Fallback based on interval string
                interval = (self.plan.interval or "").lower()
                if 'year' in interval or 'annual' in interval:
                    duration_days = 365
                elif 'month' in interval:
                    duration_days = 30
                elif 'week' in interval:
                    duration_days = 7

        # 2. Determine Status & Renewal Date
        # If price > 0, it's a paid active plan. Otherwise, it's a trial.
        if self.plan and self.plan.price > 0:
            self.status = 'active'
            self.renewal_date = now() + timedelta(days=duration_days)
        else:
            self.status = 'trial'
            self.renewal_date = now() + timedelta(days=TRIAL_PERIOD_DAYS)

        self.save()

    # ---------------------------
    # Check if active & valid
    # ---------------------------
    def is_active_and_valid(self):
        """
        Checks if subscription is active/trial and not expired.
        Auto-updates status to expired if date passed.
        """
        if self.status not in ['active', 'trial']:
            return False

        if self.renewal_date and now() > self.renewal_date:
            self.status = 'expired'
            self.save()
            return False

        return True
    
    # ---------------------------
    # Start Trial Subscription
    # ---------------------------
    def start_trial(self):
        self.status = 'trial'
        self.renewal_date = now() + timedelta(days=TRIAL_PERIOD_DAYS)
        self.save()

    def __str__(self):
        plan_name = self.plan.name if self.plan else 'No Plan'
        return f"{self.user.email} - {plan_name} ({self.status})"