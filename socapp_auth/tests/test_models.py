from django.test import TestCase
from django.utils import timezone

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
        self.enter_predictions(self.user)

    ### NON TEST HELPER METHODS ###
    # Queries the m2m table storing user points per tournament
    def enter_predictions(self, user, team1_goals=1, team2_goals=1):
        for f in self.wc_fixtures:
            helpers.generate_answer(user, f, team1_goals, team2_goals) # generate answers for all fixtures in the tournament
        for f in self.cl_fixtures:
            helpers.generate_answer(user, f, team1_goals, team2_goals) # generate answers for all fixtures in the tournament

    def tournament_pts(self):
        return self.user.profile.tournament_pts.filter(tournament=self.world_cup).get().points
    
    # Enters some dummy results for first two games in each tournament.
    def enter_results(self):
        for fix in self.wc_fixtures[:2]:
            helpers.play_match(fix, 1, 1)
        helpers.play_match(self.cl_fixtures[0], 1, 1)
        helpers.play_match(self.cl_fixtures[1], 2, 0)

        self.user.refresh_from_db() # grab the user from the DB, now that their points are added
        self.WC_POINTS = 10
        self.CL_POINTS = 6

    def add_friends(self, user, friendlist):
        for friend in friendlist:
            user.profile.friends.add(friend)
        user.refresh_from_db()

    ### TESTS ###

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
        cl_rm_fixtures = self.cl_fixtures[:4] # First 4 fixtures
        # remove some answers for testing
        Answer.objects.filter(user=self.user, fixture=self.wc_fixtures.last()).delete()
        Answer.objects.filter(user=self.user, fixture__in=cl_rm_fixtures).delete()

        # Test WC fixtures
        wc_answered_fixtures = Answer.objects.filter(user=self.user, fixture__tournament=self.world_cup)
        wc_answered_fixtures_pks = wc_answered_fixtures.values_list("fixture__pk", flat=True)
        no_prediction_wc = Fixture.objects.filter(tournament=self.world_cup).exclude(pk__in=wc_answered_fixtures_pks)
        self.assertQuerysetEqual(no_prediction_wc, self.user.profile.fixtures_with_no_prediction(tournament=self.world_cup), transform=lambda x: x)
        self.assertQuerysetEqual(wc_answered_fixtures, self.user.profile.get_predictions(tournament=self.world_cup), ordered=False, transform=lambda x:x)

        # Test Champions League fixtures
        cl_answered_fixtures = Answer.objects.filter(user=self.user, fixture__tournament=self.champ_lg)
        cl_answered_fixtures_pks = cl_answered_fixtures.values_list("fixture__pk", flat=True)
        no_prediction_cl = Fixture.objects.filter(tournament=self.champ_lg).exclude(pk__in=cl_answered_fixtures_pks)
        self.assertQuerysetEqual(no_prediction_cl, self.user.profile.fixtures_with_no_prediction(tournament=self.champ_lg), transform=lambda x:x)
        self.assertQuerysetEqual(cl_answered_fixtures, self.user.profile.get_predictions(tournament=self.champ_lg), ordered=False, transform=lambda x:x)

    def test_get_tournament_points(self):
        self.enter_results()
        wc_pts = self.user.profile.get_tournament_points(tournament=self.world_cup)
        self.assertEqual(wc_pts, self.WC_POINTS)

        cl_pts = self.user.profile.get_tournament_points(tournament=self.champ_lg)
        self.assertEquals(cl_pts, self.CL_POINTS)

        # Create fake tournament and assert the points = 0
        t = Tournament.objects.create(name="Atlantic League", start_date=timezone.now())
        t_pts = self.user.profile.get_tournament_points(tournament=t)
        self.assertEquals(t_pts, 0)
        self.assertEquals(self.user.profile.points, (wc_pts + cl_pts + t_pts))

    # Tests the user's points per fixture method, globally and with a provided tournament
    def test_points_per_fixture(self):
        self.enter_results()
        total_pts = self.user.profile.points

        wc_pts = self.user.profile.get_tournament_points(tournament=self.world_cup)
        cl_pts = self.user.profile.get_tournament_points(tournament=self.champ_lg)

        user_points = Answer.objects.filter(user=self.user, points_added=True)
        avg_pts = total_pts / user_points.count()
        avg_pts_wc = wc_pts / user_points.filter(fixture__tournament=self.world_cup).count()
        avg_pts_cl = cl_pts / user_points.filter(fixture__tournament=self.champ_lg).count()

        self.assertEquals(self.user.profile.points_per_fixture(), avg_pts)
        self.assertEquals(self.user.profile.points_per_fixture(tournament=self.world_cup), avg_pts_wc)
        self.assertEquals(self.user.profile.points_per_fixture(tournament=self.champ_lg), avg_pts_cl)

    # Tests the get_ranking functionality
    def test_get_ranking(self):
        user2 = helpers.generate_user(username="test2")
        self.enter_predictions(user2, 2, 2)
        self.enter_results()
        user2_wc_pts = 6
        user2_cl_pts = 3
        user2.refresh_from_db()

        self.assertEquals(user2.profile.points, user2_cl_pts + user2_wc_pts)
        self.assertEquals(user2.profile.get_tournament_points(tournament=self.world_cup), user2_wc_pts)
        self.assertEquals(user2.profile.get_tournament_points(tournament=self.champ_lg), user2_cl_pts)

        # Ensure self.user has more points for each tournament than user2
        assert self.user.profile.get_tournament_points(tournament=self.world_cup) > user2.profile.get_tournament_points(tournament=self.world_cup)
        assert self.user.profile.get_tournament_points(tournament=self.champ_lg) > user2.profile.get_tournament_points(tournament=self.champ_lg)
        u1_rank = self.user.profile.get_ranking()
        u2_rank = user2.profile.get_ranking()
        self.assertEquals(u1_rank, 1)
        self.assertEquals(u2_rank, 2)

        # Create dummy user and ensure they're ranked below user2
        user3 = helpers.generate_user(username="test3")
        u3_rank = user3.profile.get_ranking()
        self.assertEquals(u3_rank, 3)

    # Tests the get_ranking method when used among friends only
    def test_get_friend_ranking(self):
        user2, user3 = helpers.generate_user(username="test2"), helpers.generate_user(username="test3")
        self.enter_predictions(user2, 1, 1)
        self.enter_predictions(user3, 0, 2)
        self.enter_results()
        user2_wc_pts, user3_wc_pts = 6, 1
        user2_cl_pts = 3, 1
        user2.refresh_from_db()
        user3.refresh_from_db()

        # The above results should see user1,user2 ranked #1 and user3 ranked #3
        self.assertEquals(self.user.profile.get_ranking(), 1)
        self.assertEquals(user2.profile.get_ranking(), 1)
        self.assertEquals(user3.profile.get_ranking(), 3)

        # since no friends have been added, the friend ranking should be #1 for all initially
        self.assertEquals(self.user.profile.get_ranking(friends=True), 1)
        self.assertEquals(user3.profile.get_ranking(friends=True), 1)

        # Add friends for user1 and check ranking among them
        self.add_friends(self.user, [user2, user3])
        self.assertEqual(self.user.profile.friends.count(), 2)
        self.assertEquals(self.user.profile.get_ranking(friends=True), 1)
        
        # Add friends for user3 and check ranking among them
        self.add_friends(user3, [user2])
        self.assertEqual(user3.profile.get_ranking(friends=True), 2)
        self.add_friends(user3, [self.user])
        self.assertEqual(user3.profile.get_ranking(friends=True), 3)
