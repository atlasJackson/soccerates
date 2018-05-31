from django.conf import settings
from django.db.models import F
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import UserProfile, Team, Fixture
import socapp.utils as utils

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

# @receiver(pre_save, sender=Fixture, dispatch_uid="update_after_result")
# def update_data_when_fixture_is_saved(sender, instance, **kwargs):
#     """
#     Update the team model based on the result of the fixture, if applicable.
#     The instance arg is the Fixture that was saved.
#     Potentially use Celery to implement this, to remove it from the HTTP request-response cycle, as it is a potentially expensive operation.
#     """
#     # The 'raw' kwarg is passed to the signal when loading data from fixtures JSON files, but not when normally saving the model. 
#     # We don't want this signal to run when loading Django fixtures, as the database won't be populated with any data prior to the fixtures being loaded in.
#     if 'raw' in kwargs and not kwargs.get('raw'):

#         # Try and retrieve previously-saved fixture from database
#         try:
#             prev_fixture = Fixture.objects.get(pk=instance.pk)
#         except Fixture.DoesNotExist:
#             return
            
#         team1, team2 = instance.team1, instance.team2

#         # If there's no result available on the previous or the updated instance, break out.
#         if not prev_fixture.result_available() and (instance.team1_goals is None or instance.team2_goals is None):
#             return

#         # If there was a previous result, but the goal fields are now set to None, then remove previous result's attrs from the Team model.
#         if prev_fixture.result_available() and (instance.team1_goals is None or instance.team2_goals is None):
#             utils.remove_team_data(prev_fixture, team1)
#             utils.remove_team_data(prev_fixture, team2)

#         elif not prev_fixture.result_available():
#             # If there was no previous result, simply add the fixture's values to the Team model
#             utils.add_team_data(instance, team1)
#             utils.add_team_data(instance, team2)
#             utils.update_user_pts()

#         else:
#             # Result already exists, so this save represents an update. Gather previous fixture data, and find differences
#             utils.update_team_data(prev_fixture, instance, team1)
#             utils.update_team_data(prev_fixture, instance, team2)