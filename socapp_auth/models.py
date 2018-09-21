from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Avg, Q
from socapp.models import Answer, Tournament, Fixture

from socapp.utils import group_users_by_points

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    picture = models.ImageField(upload_to='profile/profile_images', blank=True)
    points = models.IntegerField(default=0) # Hold the TOTAL points for the user over all tournaments.
    friends = models.ManyToManyField(settings.AUTH_USER_MODEL)

    # Stores points PER tournament for each tournament a user participates in
    tournament_points = models.ManyToManyField(Tournament, through='TournamentPoints')

    # Returns all the user's predictions, filtered by tournament if arg is provided
    def get_predictions(self, tournament=None):
        base_qs = Answer.objects.filter(user=self.user).select_related('fixture', 'user')
        if tournament is None:
            return base_qs
        else:
            return base_qs.filter(fixture__tournament=tournament)

    # Finds any fixtures for which the user has not made a prediction
    def fixtures_with_no_prediction(self, tournament, stage=None):
        user_predictions = self.get_predictions(tournament).values('fixture')
        if stage is not None:
            fixtures = tournament.all_fixtures_by_stage(stage).exclude(pk__in=user_predictions)
        else:
            fixtures = tournament.get_fixtures().exclude(pk__in=user_predictions)
        return fixtures

    # Gets the user's points for the given tournament
    def get_tournament_points(self, tournament):
        tournament_pts = self.tournament_pts.filter(tournament=tournament) # Looks at the M2M model
        if tournament_pts.exists():
            user_pts = tournament_pts.get().points
        else:
            user_pts = 0
        return user_pts

    # Returns user's rank in the system compared to all other users, or only their friends is the friends kwarg is set
    # Extend for tournament?
    def get_ranking(self, friends=False):
        if friends:
            friend_pks = self.friends.all().values_list('pk', flat=True)
            qs = get_user_model().objects.filter(Q(pk__in=friend_pks) | Q(pk=self.user.pk))
            ranked_users = group_users_by_points(qs)
        else:
            ranked_users = group_users_by_points() # Groups users into sublists: each sublist has users with the same number of points.

        # something else for ranking leaderboards?

        # Iterates over the ranked sublists, finds which one the user is in, and returns the ranking
        ranking = 1
        for grouping in ranked_users:
            if self.user in grouping:
                return ranking
            else:
                ranking += len(grouping) # Increment the ranking by however many users were in the previous sublist
        return None

    # Gets the provided user's average points per fixture, globally or for the tournament passed in
    def points_per_fixture(self, tournament=None):
        answers = self.get_predictions().filter(points_added=True)
        if tournament is not None:
            answers = answers.filter(fixture__tournament=tournament)
            
        avg_points = answers.aggregate(avg=Avg('points'))['avg']
        if avg_points is not None:
            return round(avg_points, 2) # User's points divided by the number of results
        else:
            return 0

    def __str__(self):
        return self.user.username

# Stores the number of points users gained in each tournament
class TournamentPoints(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="tournament_pts")
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="user_pts")
    points = models.IntegerField(default=0) # How many points the user got in the given tournament

    class Meta:
        unique_together = ['user', 'tournament']