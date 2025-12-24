from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils.timezone import now, timedelta

from payment.models import Plan, Subscription

User = get_user_model()

@receiver(post_save, sender=User)
def create_trial_subscription(sender, instance, created, **kwargs):
    if not created:
        return

    trial_plan = Plan.objects.filter(
        name='trial',
        is_active=True
    ).first()

    if not trial_plan:
        return

    Subscription.objects.create(
        user=instance,
        plan=trial_plan,
        status='trial',
        start_date=now(),
        renewal_date=now() + timedelta(days=trial_plan.duration_days)
    )
