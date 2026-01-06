from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Subscription, Plan

User = get_user_model()

@receiver(post_save, sender=User)
def create_subscription_for_new_user(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        sub, _ = Subscription.objects.get_or_create(user=instance)
        # Prefer a Plan named "trial" else any free plan (price == 0)
        trial_plan = Plan.objects.filter(name__iexact='trial').first() or Plan.objects.filter(price=0).first()
        if trial_plan:
            sub.plan = trial_plan
        sub.start_trial()
    except Exception:
        # Do not block user creation on errors
        pass
