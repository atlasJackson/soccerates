from django.conf import settings
from django.db import models
from socapp.models import Answer, Tournament

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    picture = models.ImageField(upload_to='profile/profile_images', blank=True)
    points = models.IntegerField(default=0) # Hold the TOTAL points for the user over all tournaments

    # Stores points PER tournament for each tournament a user participates in
    tournament_points = models.ManyToManyField(Tournament, through='TournamentPoints')

    def get_predictions(self):
        return Answer.objects.select_related('fixture', 'user', 'fixture__team1', 'fixture__team2') \
            .filter(user=self.user)

    def __str__(self):
        return self.user.username

# Stores the number of points users gained in each tournament
class TournamentPoints(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="t_pts")
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="tournament")
    points = models.IntegerField(default=0) # How many points the user got in the given tournament

    class Meta:
        unique_together = ['user', 'tournament']