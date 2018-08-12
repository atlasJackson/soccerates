from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import UserProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """ Creates a UserProfile instance whenever a new User is created """
    if created:
        # The instance arg is the User instance that triggered the signal
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()

@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def delete_userprofile(sender, instance, **kwargs):
    if getattr(instance, "profile", None) is not None:
        UserProfile.objects.get(user_id=instance.pk).delete()