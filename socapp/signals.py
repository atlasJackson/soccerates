from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, Team

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """ Creates a UserProfile instance whenever a new User is created """
    if created:
        # The instance arg is the User instance that triggered the signal
        UserProfile.objects.create(user=instance)#
    else:
        instance.profile.save()

@receiver(post_save, sender=Team)
def generate_flag_path(sender, instance, created, **kwargs):
    """ 
    Generates the path to the team's flag image
    The flag image files are all PNGs with name equal to the name of the country, in lowercase, with spaces removed.
    Below: we convert the team name to that format, and save the path to the image 
    """
    if created:
        team_name = instance.name.lower().replace(" ", "")
        instance.flag = "img/{}.png".format(team_name)
        instance.save()