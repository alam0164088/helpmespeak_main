from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from .models import User, Profile

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # নতুন ইউজারের জন্য profile create
        Profile.objects.create(user=instance)
    else:
        try:
            profile = instance.profile
        except ObjectDoesNotExist:
            Profile.objects.create(user=instance)
        else:
            profile.save()
