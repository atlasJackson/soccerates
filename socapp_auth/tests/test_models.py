from django.test import TestCase

from socapp.models import *
import socapp.tests.test_helpers as helpers

from socapp_auth.models import UserProfile, TournamentPoints

class UserProfileTests(TestCase):
    fixtures = ['tournaments.json', 'teams.json', 'games.json', 'teams_champ_lg', 'games_champ_lg']

    def setUp(self):
        self.user = helpers.generate_user()
        self.world_cup = Tournament.objects.filter(name="World Cup 2018").get()
        self.champ_lg = Tournament.objects.filter(name="UEFA Champions League 2018").get()
        self.wc_fixtures = Fixture.objects.filter(tournament=self.world_cup)
        self.cl_fixtures = Fixture.objects.filter(tournament=self.champ_lg)
        for f in self.wc_fixtures:
            helpers.generate_answer(self.user, f) # generate answers for all fixtures in the tournament
        for f in self.cl_fixtures:
            helpers.generate_answer(self.user, f) # generate answers for all fixtures in the tournament

    # Queries the m2m table storing user points per tournament
    def tournament_pts(self):
        return self.user.profile.tournament_pts.filter(tournament=self.world_cup).get().points

    # Tests to ensure a UserProfile is also created whenever a user is created
    def test_userprofile_creation(self):
        self.assertIsInstance(self.user.profile, UserProfile)
    
    # Tests that users have zero points upon creation
    def test_user_starts_with_zero_points(self):
        self.assertEquals(self.user.profile.points, 0)
        with self.assertRaises(TournamentPoints.DoesNotExist):
            self.assertEquals(self.tournament_pts(), 0)

    # Tests the user profile method that returns the fixtures for which the user has made a prediction
    def test_get_predictions(self):
        user_answers_all = Answer.objects.filter(user=self.user)
        user_answers_wc = Answer.objects.filter(fixture__tournament=self.world_cup, user=self.user)
        user_answers_cl = Answer.objects.filter(fixture__tournament=self.champ_lg, user=self.user)

        predictions_all = self.user.profile.get_predictions()
        predictions_wc = self.user.profile.get_predictions(tournament=self.world_cup)
        predictions_cl = self.user.profile.get_predictions(tournament=self.champ_lg)
        
        self.assertQuerysetEqual(user_answers_all, predictions_all, ordered=False, transform=lambda x: x)
        self.assertQuerysetEqual(user_answers_wc, predictions_wc, ordered=False, transform=lambda x: x)
        self.assertQuerysetEqual(user_answers_cl, predictions_cl, ordered=False, transform=lambda x: x)
    
    # Tests the method returning fixtures for which the user has not made any predictions
    def test_fixtures_with_no_prediction(self):
        wc_rm_fixture = self.wc_fixtures.last()
        cl_rm_fixtures = self.cl_fixtures[:4] # First 4 fixtures
        # remove some answers for testing
        Answer.objects.filter(user=self.user, fixture=wc_rm_fixture).delete()
        Answer.objects.filter(user=self.user, fixture__in=cl_rm_fixtures).delete()
        wc_answered_fixture_pks = Answer.objects.filter(user=self.user, fixture__tournament=self.world_cup).values_list("fixture__pk", flat=True)
        no_prediction_wc = Fixture.objects.filter(tournament=self.world_cup).exclude(pk__in=wc_answered_fixture_pks)
        self.assertQuerysetEqual(no_prediction_wc, self.user.profile.fixtures_with_no_prediction(tournament=self.world_cup), transform=lambda x: x)

        cl_answered_fixture_pks = Answer.objects.filter(user=self.user, fixture__tournament=self.champ_lg).values_list("fixture__pk", flat=True)
        no_prediction_cl = Fixture.objects.filter(tournament=self.champ_lg).exclude(pk__in=cl_answered_fixture_pks)
        self.assertQuerysetEqual(no_prediction_cl, self.user.profile.fixtures_with_no_prediction(tournament=self.champ_lg), transform=lambda x:x)