from django.db import models
from django.conf import settings
from django.utils.timezone import now
from datetime import timedelta

# Use short free trial: 5 minutes (for testing/demo). No DB migration needed.
TRIAL_PERIOD_MINUTES = 5

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
    duration_days = models.IntegerField(default=30)  # প্ল্যান কতদিন চলবে
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
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(auto_now_add=True)
    renewal_date = models.DateTimeField(null=True, blank=True)
    latest_receipt_token = models.CharField(max_length=512, null=True, blank=True)
    platform = models.CharField(max_length=10, null=True, blank=True)
    
    # ---------------------------
    # Activate Subscription
    # ---------------------------
    def activate(self, plan=None):
        """
        Subscription activate করবে। 
        যদি plan দেওয়া হয়, সেটি assign করবে।
        """
        if plan:
            self.plan = plan
            # set trial / first billing period to 7 days
            self.renewal_date = now() + timedelta(days=7)
            self.status = 'trial'  # or 'active' depending on your logic
            self.is_active = True
            self.save()

    # ---------------------------
    # Check if active & valid
    # ---------------------------
    def is_active_and_valid(self):
        """
        Returns True যদি subscription active/trial এবং expired না হয়।
        Expired হলে auto update করবে status।
        """
        if self.status not in ['active', 'trial']:
            return False

        if self.renewal_date and now() > self.renewal_date:
            self.status = 'expired'
            self.save()
            return False

        return True
    
    # ---------------------------
    # Check if Pro (paid) active
    # ---------------------------
    def is_active_pro(self):
        """
        Returns True যদি subscription paid এবং active হয়
        """
        return self.status == 'active' and self.plan and self.plan.price > 0

    # ---------------------------
    # Start Trial Subscription
    # ---------------------------
    def start_trial(self):
        # short trial for new accounts: 5 minutes from now
        self.status = 'trial'
        self.renewal_date = now() + timedelta(minutes=TRIAL_PERIOD_MINUTES)
        self.save()

    def __str__(self):
        return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'} ({self.status})"