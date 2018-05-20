from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """ Creates a UserProfile instance whenever a new User is created """
    if created:
        # The instance arg is the User instance that triggered the signal
        UserProfile.objects.create(user=instance)
