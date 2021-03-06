from django.db.models import Q, F, When, Case, Value, Sum, IntegerField
from django.test import TestCase
from django.utils import timezone
import socapp.tests.test_helpers as helpers

from socapp.models import *

""" 
More in depth testing of the application's ability to propagate the result of a Fixture to related Team model fields, and to generate each user's points for the fixture.
When a result is entered, the user's points should be calculated based on the accuracy of their prediction.
"""

class ResultEnteredTests(TestCase):
    fixtures = ['tournaments.json', 'teams.json', 'games.json']
    
    results = [
        { 'team1_goals': 2, 'team2_goals': 1 }, # Russia vs Saudi Arabia
        { 'team1_goals': 0, 'team2_goals': 0 }, # Egypt vs Uruguay
        { 'team1_goals': 4, 'team2_goals': 3 }, # Russia vs Egypt
        { 'team1_goals': 2, 'team2_goals': 2 }, # Uruguay vs Saudi Arabia
        { 'team1_goals': 1, 'team2_goals': 3 }, # Saudi Arabia vs Egypt
        { 'team1_goals': 5, 'team2_goals': 1 }  # Uruguay vs Russia
    ]

    user_predictions = [
        { 'team1_goals': 2, 'team2_goals': 1 }, # Should return 5 points
        { 'team1_goals': 2, 'team2_goals': 2 }, # Should return 3 points
        { 'team1_goals': 0, 'team2_goals': 3 }, # Should return 0 points
        { 'team1_goals': 1, 'team2_goals': 3 }, # Should return 1 point
        { 'team1_goals': 2, 'team2_goals': 4 }, # Should return 3 points
        { 'team1_goals': 1, 'team2_goals': 0 } # Should return 2 points
    ]

    user2_predictions = [
        { 'team1_goals': 2, 'team2_goals': 2 }, # Should return 0 points
        { 'team1_goals': 2, 'team2_goals': 0 }, # Should return 0 points
        { 'team1_goals': 2, 'team2_goals': 1 }, # Should return 3 points
        { 'team1_goals': 1, 'team2_goals': 0 }, # Should return 0 points
        { 'team1_goals': 1, 'team2_goals': 3 }, # Should return 5 points
        { 'team1_goals': 6, 'team2_goals': 0 } # Should return 3 points
    ]

    user3_predictions = [
        { 'team1_goals': 2, 'team2_goals': 1 },
        { 'team1_goals': 0, 'team2_goals': 0 },
        { 'team1_goals': 4, 'team2_goals': 3 },
        { 'team1_goals': 2, 'team2_goals': 2 },
        { 'team1_goals': 1, 'team2_goals': 3 },
        { 'team1_goals': 5, 'team2_goals': 1 } 
    ]

    updated_results = [
        { 'team1_goals': 2, 'team2_goals': 0 }, # Russia vs Saudi Arabia (-3)
        { 'team1_goals': 3, 'team2_goals': 2 }, # Egypt vs Uruguay (-5)
        { 'team1_goals': 4, 'team2_goals': 5 }  # Russia vs Egypt (-5)
    ]

    USER1_TOTAL_POINTS = 14 # Based on the above predictions
    USER1_UPDATED_TOTAL_POINTS = 10

    USER2_TOTAL_POINTS = 11
    USER2_UPDATED_TOTAL_POINTS = 10

    USER3_TOTAL_POINTS = 30
    USER3_UPDATED_TOTAL_POINTS = 17

    # Sets the test class up for each test method
    def setUp(self):
        self.user = helpers.generate_user(username="test", password="password")
        self.user2 = helpers.generate_user(username="test2", password="password")
        self.user3 = helpers.generate_user(username="username", password="password")
        self.tournament = Tournament.objects.first()
        
        self.add_predictions(self.user, self.user_predictions)
        self.add_predictions(self.user2, self.user2_predictions)
        self.add_predictions(self.user3, self.user3_predictions)
        self.add_results()
        self.russia = Team.objects.get(name="Russia")
        self.saudi = Team.objects.get(name="Saudi Arabia")
        self.egypt = Team.objects.get(name="Egypt")
        self.uruguay = Team.objects.get(name="Uruguay")

        self.russia_fixtures = self.russia.get_fixtures()
        self.saudi_fixtures = self.saudi.get_fixtures()
        self.egypt_fixtures = self.egypt.get_fixtures()
        self.uruguay_fixtures = self.uruguay.get_fixtures()
    
    # Queries the m2m table storing user points per tournament
    def tournament_pts(self, user):
        return user.profile.tournament_pts.filter(tournament=self.tournament).get().points

    #############
    #  Tests for adding results, and ensuring the updates propagate correctly to the Team model
    ##

    # Tests that values on the Team model's games_for field are correct after adding Fixture results
    def test_team_goals_for_field(self):
        russia_goals = self.total_goals_scored(self.russia_fixtures, self.russia)
        saudi_goals = self.total_goals_scored(self.saudi_fixtures, self.saudi)
        egypt_goals = self.total_goals_scored(self.egypt_fixtures, self.egypt)
        uruguay_goals = self.total_goals_scored(self.uruguay_fixtures, self.uruguay)
        self.assertEquals(russia_goals, self.russia.goals_for)
        self.assertEquals(russia_goals, self.russia.group_goals_for)
        self.assertEquals(saudi_goals, self.saudi.goals_for)
        self.assertEquals(saudi_goals, self.saudi.group_goals_for)
        self.assertEquals(egypt_goals, self.egypt.goals_for)
        self.assertEquals(egypt_goals, self.egypt.group_goals_for)
        self.assertEquals(uruguay_goals, self.uruguay.goals_for)
        self.assertEquals(uruguay_goals, self.uruguay.group_goals_for)

    # Tests that values on the Team model's goals_against field are correct after adding Fixture results
    def test_team_goals_against_field(self):
        russia_conceded = self.total_goals_conceded(self.russia_fixtures, self.russia)
        saudi_conceded = self.total_goals_conceded(self.saudi_fixtures, self.saudi)
        egypt_conceded = self.total_goals_conceded(self.egypt_fixtures, self.egypt)
        uruguay_conceded = self.total_goals_conceded(self.uruguay_fixtures, self.uruguay)
        self.assertEquals(russia_conceded, self.russia.goals_against)
        self.assertEquals(russia_conceded, self.russia.group_goals_against)
        self.assertEquals(saudi_conceded, self.saudi.goals_against)
        self.assertEquals(saudi_conceded, self.saudi.group_goals_against)
        self.assertEquals(egypt_conceded, self.egypt.goals_against)
        self.assertEquals(egypt_conceded, self.egypt.group_goals_against)
        self.assertEquals(uruguay_conceded, self.uruguay.goals_against)
        self.assertEquals(uruguay_conceded, self.uruguay.group_goals_against)

    # Tests that values on the Team model's games_won field are correct after adding Fixture results
    def test_team_games_won_field(self):
        russia_won = self.total_games_won(self.russia_fixtures, self.russia)
        saudi_won = self.total_games_won(self.saudi_fixtures, self.saudi)
        egypt_won = self.total_games_won(self.egypt_fixtures, self.egypt)
        uruguay_won = self.total_games_won(self.uruguay_fixtures, self.uruguay)
        self.assertEquals(russia_won, self.russia.games_won)
        self.assertEquals(russia_won, self.russia.group_won)
        self.assertEquals(saudi_won, self.saudi.games_won)
        self.assertEquals(saudi_won, self.saudi.group_won)
        self.assertEquals(egypt_won, self.egypt.games_won)
        self.assertEquals(egypt_won, self.egypt.group_won) 
        self.assertEquals(uruguay_won, self.uruguay.games_won)
        self.assertEquals(uruguay_won, self.uruguay.group_won)

    # Tests that values on the Team model's games_drawn field are correct after adding Fixture results
    def test_team_games_drawn_field(self):
        russia_drawn = self.total_games_drawn(self.russia_fixtures, self.russia)
        saudi_drawn = self.total_games_drawn(self.saudi_fixtures, self.saudi)
        egypt_drawn = self.total_games_drawn(self.egypt_fixtures, self.egypt)
        uruguay_drawn = self.total_games_drawn(self.uruguay_fixtures, self.uruguay)
        self.assertEquals(russia_drawn, self.russia.games_drawn)
        self.assertEquals(russia_drawn, self.russia.group_drawn)
        self.assertEquals(saudi_drawn, self.saudi.games_drawn)
        self.assertEquals(saudi_drawn, self.saudi.group_drawn)
        self.assertEquals(egypt_drawn, self.egypt.games_drawn)
        self.assertEquals(egypt_drawn, self.egypt.group_drawn)
        self.assertEquals(uruguay_drawn, self.uruguay.games_drawn)
        self.assertEquals(uruguay_drawn, self.uruguay.group_drawn)

    # Tests that values on the Team model's games_lost field are correct after adding Fixture results
    def test_team_games_lost_field(self):
        russia_lost = self.total_games_lost(self.russia_fixtures, self.russia)
        saudi_lost = self.total_games_lost(self.saudi_fixtures, self.saudi)
        egypt_lost = self.total_games_lost(self.egypt_fixtures, self.egypt)
        uruguay_lost = self.total_games_lost(self.uruguay_fixtures, self.uruguay)
        self.assertEquals(russia_lost, self.russia.games_lost)
        self.assertEquals(russia_lost, self.russia.group_lost)
        self.assertEquals(saudi_lost, self.saudi.games_lost)
        self.assertEquals(saudi_lost, self.saudi.group_lost)
        self.assertEquals(egypt_lost, self.egypt.games_lost)
        self.assertEquals(egypt_lost, self.egypt.group_lost)
        self.assertEquals(uruguay_lost, self.uruguay.games_lost)
        self.assertEquals(uruguay_lost, self.uruguay.group_lost)

    # Tests that values on the Team model's points field are correct after adding Fixture results    
    def test_team_points_field(self):
        self.assertEquals(self.russia.points, 6)
        self.assertEquals(self.saudi.points, 1)
        self.assertEquals(self.egypt.points, 4)
        self.assertEquals(self.uruguay.points, 5)

    # Tests that values on the Team model's games_played field are correct after adding Fixture results
    def test_team_games_played_field(self):
        self.assertEquals(self.russia.games_played, 3)
        self.assertEquals(self.saudi.games_played, 3)
        self.assertEquals(self.egypt.games_played, 3)
        self.assertEquals(self.uruguay.games_played, 3)

    #############
    #  Tests for updating some of the results, and ensuring the updates propagate correctly
    ##

    # Tests that updated values on the Team model's games_won field are correct after applying Fixture update
    def test_updated_goals_for_field(self):
        russia_goals = self.total_goals_scored(self.russia_fixtures, self.russia, apply_update=True)
        saudi_goals = self.total_goals_scored(self.saudi_fixtures, self.saudi, apply_update=True)
        egypt_goals = self.total_goals_scored(self.egypt_fixtures, self.egypt, apply_update=True)
        uruguay_goals = self.total_goals_scored(self.uruguay_fixtures, self.uruguay, apply_update=True)
        self.assertEquals(russia_goals, self.russia.goals_for)
        self.assertEquals(russia_goals, self.russia.group_goals_for)
        self.assertEquals(saudi_goals, self.saudi.goals_for)
        self.assertEquals(saudi_goals, self.saudi.group_goals_for)
        self.assertEquals(egypt_goals, self.egypt.goals_for)
        self.assertEquals(egypt_goals, self.egypt.group_goals_for)
        self.assertEquals(uruguay_goals, self.uruguay.goals_for)
        self.assertEquals(uruguay_goals, self.uruguay.group_goals_for)

    # Tests that updated values on the Team model's goals_against field are correct after applying Fixture update
    def test_updated_goals_against_field(self):
        russia_conceded = self.total_goals_conceded(self.russia_fixtures, self.russia, apply_update=True)
        saudi_conceded = self.total_goals_conceded(self.saudi_fixtures, self.saudi, apply_update=True)
        egypt_conceded = self.total_goals_conceded(self.egypt_fixtures, self.egypt, apply_update=True)
        uruguay_conceded = self.total_goals_conceded(self.uruguay_fixtures, self.uruguay, apply_update=True)
        self.assertEquals(russia_conceded, self.russia.goals_against)
        self.assertEquals(russia_conceded, self.russia.group_goals_against)
        self.assertEquals(saudi_conceded, self.saudi.goals_against)
        self.assertEquals(saudi_conceded, self.saudi.group_goals_against)
        self.assertEquals(egypt_conceded, self.egypt.goals_against)
        self.assertEquals(egypt_conceded, self.egypt.group_goals_against)
        self.assertEquals(uruguay_conceded, self.uruguay.goals_against)
        self.assertEquals(uruguay_conceded, self.uruguay.group_goals_against)

    # Tests that updated values on the Team model's games_won field are correct after applying Fixture update
    def test_updated_games_won_field(self):
        russia_won = self.total_games_won(self.russia_fixtures, self.russia, apply_update=True)
        saudi_won = self.total_games_won(self.saudi_fixtures, self.saudi, apply_update=True)
        egypt_won = self.total_games_won(self.egypt_fixtures, self.egypt, apply_update=True)
        uruguay_won = self.total_games_won(self.uruguay_fixtures, self.uruguay, apply_update=True)
        self.assertEquals(russia_won, self.russia.games_won)
        self.assertEquals(russia_won, self.russia.group_won)
        self.assertEquals(saudi_won, self.saudi.games_won)
        self.assertEquals(saudi_won, self.saudi.group_won)
        self.assertEquals(egypt_won, self.egypt.games_won)
        self.assertEquals(egypt_won, self.egypt.group_won)
        self.assertEquals(uruguay_won, self.uruguay.games_won)
        self.assertEquals(uruguay_won, self.uruguay.group_won)

    # Tests that updated values on the Team model's games_drawn field are correct after applying Fixture update    
    def test_updated_games_drawn_field(self):
        russia_drawn = self.total_games_drawn(self.russia_fixtures, self.russia, apply_update=True)
        saudi_drawn = self.total_games_drawn(self.saudi_fixtures, self.saudi, apply_update=True)
        egypt_drawn = self.total_games_drawn(self.egypt_fixtures, self.egypt, apply_update=True)
        uruguay_drawn = self.total_games_drawn(self.uruguay_fixtures, self.uruguay, apply_update=True)
        self.assertEquals(russia_drawn, self.russia.games_drawn)
        self.assertEquals(russia_drawn, self.russia.group_drawn)
        self.assertEquals(saudi_drawn, self.saudi.games_drawn)
        self.assertEquals(saudi_drawn, self.saudi.group_drawn)
        self.assertEquals(egypt_drawn, self.egypt.games_drawn)
        self.assertEquals(egypt_drawn, self.egypt.group_drawn)
        self.assertEquals(uruguay_drawn, self.uruguay.games_drawn)
        self.assertEquals(uruguay_drawn, self.uruguay.group_drawn)

    # Tests that updated values on the Team model's games_lost field are correct after applying Fixture update
    def test_updated_games_lost_field(self):
        russia_lost = self.total_games_lost(self.russia_fixtures, self.russia, apply_update=True)
        saudi_lost = self.total_games_lost(self.saudi_fixtures, self.saudi, apply_update=True)
        egypt_lost = self.total_games_lost(self.egypt_fixtures, self.egypt, apply_update=True)
        uruguay_lost = self.total_games_lost(self.uruguay_fixtures, self.uruguay, apply_update=True)
        self.assertEquals(russia_lost, self.russia.games_lost)
        self.assertEquals(russia_lost, self.russia.group_lost)
        self.assertEquals(saudi_lost, self.saudi.games_lost)
        self.assertEquals(saudi_lost, self.saudi.group_lost)
        self.assertEquals(egypt_lost, self.egypt.games_lost)
        self.assertEquals(egypt_lost, self.egypt.group_lost)
        self.assertEquals(uruguay_lost, self.uruguay.games_lost)
        self.assertEquals(uruguay_lost, self.uruguay.group_lost)

    # Ensures that on update, extra games are not added to the team's games_played field
    def test_updated_games_played(self):
        self.update_fixtures()
        self.assertEquals(self.russia.games_played, 3)
        self.assertEquals(self.saudi.games_played, 3)
        self.assertEquals(self.egypt.games_played, 3)
        self.assertEquals(self.uruguay.games_played, 3)

    # Tests teams when all matches are set to 0-0
    def test_all_nil_nil(self):
        self.update_fixtures_to_nil_nil()
        for team in Team.objects.filter(group="A"):
            self.assertEquals(team.games_played, 3)
            self.assertEquals(team.games_won, 0)
            self.assertEquals(team.games_drawn, 3)
            self.assertEquals(team.games_lost, 0)
            self.assertEquals(team.goals_for, 0)
            self.assertEquals(team.goals_against, 0)
            self.assertEquals(team.group_goals_for, 0)
            self.assertEquals(team.group_goals_against, 0)
            self.assertEquals(team.group_won, 0)
            self.assertEquals(team.group_drawn, 3)
            self.assertEquals(team.group_lost, 0)
            self.assertEquals(team.points, 3)

    # Test for removing all results: does the Team model revert to its initial state (all 0s)?
    def test_team_model_after_results_are_removed(self):
        self.remove_all_results()
        teams = Team.objects.filter(group="A")
        for team in teams:
            self.assertEquals(team.games_played, 0)
            self.assertEquals(team.games_won, 0)
            self.assertEquals(team.games_drawn, 0)
            self.assertEquals(team.games_lost, 0)
            self.assertEquals(team.goals_for, 0)
            self.assertEquals(team.goals_against, 0)
            self.assertEquals(team.group_goals_for, 0)
            self.assertEquals(team.group_goals_against, 0)
            self.assertEquals(team.group_won, 0)
            self.assertEquals(team.group_drawn, 0)
            self.assertEquals(team.group_lost, 0)
            self.assertEquals(team.points, 0)
            self.assertEquals(team.goal_difference, 0)

    # Removes a single result, and checks that the Team model values update accordingly
    def test_team_model_after_particular_result_is_removed(self):
        fixture = Fixture.objects.first()
        fixture.team1_goals = None
        fixture.team2_goals = None
        fixture.save()
        self.assertEquals(fixture.team1.goals_for, 5)
        self.assertEquals(fixture.team1.group_goals_for, 5)
        self.assertEquals(fixture.team2.goals_for, 3)
        self.assertEquals(fixture.team2.group_goals_for, 3)
        self.assertEquals(fixture.team1.goals_against, 8)
        self.assertEquals(fixture.team1.group_goals_against, 8)
        self.assertEquals(fixture.team2.goals_against, 5)
        self.assertEquals(fixture.team2.group_goals_against, 5)
        self.assertEquals(fixture.team1.games_played, 2)
        self.assertEquals(fixture.team2.games_played, 2)
        self.assertEquals(fixture.team1.games_won, 1)
        self.assertEquals(fixture.team1.group_won, 1)
        self.assertEquals(fixture.team2.games_won, 0)
        self.assertEquals(fixture.team2.group_won, 0)
        self.assertEquals(fixture.team1.games_drawn, 0)
        self.assertEquals(fixture.team1.group_drawn, 0)
        self.assertEquals(fixture.team2.games_drawn, 1)
        self.assertEquals(fixture.team2.group_drawn, 1)
        self.assertEquals(fixture.team1.games_lost, 1)
        self.assertEquals(fixture.team1.group_lost, 1)
        self.assertEquals(fixture.team2.games_lost, 1)
        self.assertEquals(fixture.team2.group_lost, 1)
        self.assertEquals(fixture.team1.points, 3)
        self.assertEquals(fixture.team2.points, 1)
    
    #############
    #  Tests for the user points
    ##
    def test_user_points(self):
        self.assertEquals(self.user.profile.points, self.USER1_TOTAL_POINTS)
        self.assertEquals(self.user2.profile.points, self.USER2_TOTAL_POINTS)
        self.assertEquals(self.user3.profile.points, self.USER3_TOTAL_POINTS)

        # Check tournament points m2m relationship
        self.assertEquals(self.tournament_pts(user=self.user), self.USER1_TOTAL_POINTS)
        self.assertEquals(self.tournament_pts(user=self.user2), self.USER2_TOTAL_POINTS)
        self.assertEquals(self.tournament_pts(user=self.user3), self.USER3_TOTAL_POINTS)

        # Check the points added flag is set to true for each answer
        for answer in Answer.objects.all():
            self.assertEquals(answer.points_added, Answer.POINTS_ADDED)

        # Test after fixtures update:
        self.update_fixtures()
        self.assertEquals(self.user.profile.points, self.USER1_UPDATED_TOTAL_POINTS)
        self.assertEquals(self.user2.profile.points, self.USER2_UPDATED_TOTAL_POINTS)
        self.assertEquals(self.user3.profile.points, self.USER3_UPDATED_TOTAL_POINTS)

        # Check tournament points m2m relationship after update
        self.assertEquals(self.tournament_pts(user=self.user), self.USER1_UPDATED_TOTAL_POINTS)
        self.assertEquals(self.tournament_pts(user=self.user2), self.USER2_UPDATED_TOTAL_POINTS)
        self.assertEquals(self.tournament_pts(user=self.user3), self.USER3_UPDATED_TOTAL_POINTS)

        # Random update: turns 0 points to 5
        f = Fixture.objects.get(team1__name="Uruguay", team2__name="Saudi Arabia")
        f.team1_goals, f.team2_goals = 1, 0
        f.save()
        self.user.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()
        self.assertEquals(self.user.profile.points, self.USER1_UPDATED_TOTAL_POINTS - 1)
        self.assertEquals(self.user2.profile.points, self.USER2_UPDATED_TOTAL_POINTS + 5)
        self.assertEquals(self.user3.profile.points, self.USER3_UPDATED_TOTAL_POINTS - 5)

        # Check tournament points m2m relationship after random update
        self.assertEquals(self.tournament_pts(user=self.user), self.USER1_UPDATED_TOTAL_POINTS - 1)
        self.assertEquals(self.tournament_pts(user=self.user2), self.USER2_UPDATED_TOTAL_POINTS + 5)
        self.assertEquals(self.tournament_pts(user=self.user3), self.USER3_UPDATED_TOTAL_POINTS - 5)

    def test_answer_points_field(self):
        user1_total_pts = Answer.objects.filter(user=self.user).aggregate(total=Sum('points'))['total']
        user2_total_pts = Answer.objects.filter(user=self.user2).aggregate(total=Sum('points'))['total']
        user3_total_pts = Answer.objects.filter(user=self.user3).aggregate(total=Sum('points'))['total']
        self.assertEquals(user1_total_pts, self.USER1_TOTAL_POINTS)
        self.assertEquals(user2_total_pts, self.USER2_TOTAL_POINTS)
        self.assertEquals(user3_total_pts, self.USER3_TOTAL_POINTS)

        self.update_fixtures()
        user1_total_pts = Answer.objects.filter(user=self.user).aggregate(total=Sum('points'))['total']
        user2_total_pts = Answer.objects.filter(user=self.user2).aggregate(total=Sum('points'))['total']
        user3_total_pts = Answer.objects.filter(user=self.user3).aggregate(total=Sum('points'))['total']
        self.assertEquals(user1_total_pts, self.USER1_UPDATED_TOTAL_POINTS)
        self.assertEquals(user2_total_pts, self.USER2_UPDATED_TOTAL_POINTS)
        self.assertEquals(user3_total_pts, self.USER3_UPDATED_TOTAL_POINTS)

        self.remove_all_results()
        user1_total_pts = Answer.objects.filter(user=self.user).aggregate(total=Sum('points'))['total']
        user2_total_pts = Answer.objects.filter(user=self.user2).aggregate(total=Sum('points'))['total']
        user3_total_pts = Answer.objects.filter(user=self.user3).aggregate(total=Sum('points'))['total']
        self.assertIsNone(user1_total_pts)
        self.assertIsNone(user2_total_pts)
        self.assertIsNone(user3_total_pts)

    def test_user_points_after_removing_all_fixtures(self):
        self.remove_all_results()
        self.assertEquals(self.user.profile.points, 0)
        self.assertEquals(self.user2.profile.points, 0)

        # Check tournament points m2m relationship
        self.assertEquals(self.tournament_pts(user=self.user), 0)
        self.assertEquals(self.tournament_pts(user=self.user2), 0)
        self.assertEquals(self.tournament_pts(user=self.user3), 0)

        # Check the points added flag is set to false for each answer
        for answer in Answer.objects.all():
            self.assertEquals(answer.points_added, Answer.POINTS_NOT_ADDED)

    def test_user_points_after_removing_individual_fixture(self):
        # Remove the fixture that got user1 five points:
        f = self.tournament.all_fixtures_by_group("A")[0]
        assert f.team1.name == "Russia" and f.team2.name == "Saudi Arabia" # Ensure it's the same fixture
        f.team1_goals = f.team2_goals = None # Invalidate the result
        f.save()
        self.assertEquals(self.user.profile.points, self.USER1_TOTAL_POINTS - 5) # Check the user's points have been reset by 5
        # Check tournament points m2m relationship
        self.assertEquals(self.tournament_pts(user=self.user), self.USER1_TOTAL_POINTS - 5)


    #############
    #  Helper methods for setting up tests, and acquiring values from the Team and Fixture models
    ##

    # Create an answer for each fixture, for the user generated in the setUp method.
    def add_predictions(self, user, predictions):
        fixtures = self.tournament.all_fixtures_by_group("A")
        assert fixtures.count() == len(predictions)
        for fixture, prediction in zip(fixtures, predictions):
            a = Answer(fixture=fixture, user=user)
            a.team1_goals = prediction['team1_goals']
            a.team2_goals = prediction['team2_goals']
            a.save()

    # Add a result for each fixture in Group A
    def add_results(self):
        fixtures = self.tournament.all_fixtures_by_group("A")
        assert fixtures.count() == len(self.results)
        for fixture, result in zip(fixtures, self.results):
            fixture.team1_goals = result['team1_goals']
            fixture.team2_goals = result['team2_goals']
            fixture.save()
        self.user.refresh_from_db()
        self.user2.refresh_from_db()            
        self.user3.refresh_from_db()            

    # Sets all fixtures' team_goals fields to None
    def remove_all_results(self):
        fixtures = self.tournament.all_fixtures_by_group("A")
        for fixture in fixtures:
            fixture.team1_goals = None
            fixture.team2_goals = None
            fixture.save()
        self.user.refresh_from_db()
        self.user2.refresh_from_db()            
        self.user3.refresh_from_db()

    # Updates the first three fixtures' results and refreshes the local team instances from the database
    def update_fixtures(self):
        fixtures = self.tournament.all_fixtures_by_group("A")[:3] # Grab the first 3 fixtures
        for fixture, result in zip(fixtures, self.updated_results):          
            fixture.team1_goals = result['team1_goals']
            fixture.team2_goals = result['team2_goals']
            fixture.save()
        self.russia.refresh_from_db()
        self.saudi.refresh_from_db()
        self.egypt.refresh_from_db()
        self.uruguay.refresh_from_db()
        self.user.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()

    # Sets all matches to 0-0
    def update_fixtures_to_nil_nil(self):
        for fixture in self.tournament.all_fixtures_by_group("A"):
            fixture.team1_goals = 0
            fixture.team2_goals = 0
            fixture.save()
        self.russia.refresh_from_db()
        self.saudi.refresh_from_db()
        self.egypt.refresh_from_db()
        self.uruguay.refresh_from_db()

    # Given a queryset, gets the total number of goals the team has scored throughout each fixture in the queryset.
    def total_goals_scored(self, queryset, team, apply_update=False):
        if apply_update:
            self.update_fixtures()
        return queryset.annotate(goals=Case(
            When(Q(team1=team), then=F('team1_goals')),
            When(Q(team2=team), then=F('team2_goals')),
            default=Value(0),
            output_field=IntegerField())).aggregate(total_goals=Sum('goals'))['total_goals']
    
    # Given a queryset, gets the total number of goals the team has conceded throughout each fixture in the queryset.
    def total_goals_conceded(self, queryset, team, apply_update=False):
        if apply_update:
            self.update_fixtures()
        return queryset.annotate(goals=Case(
            When(Q(team1=team), then=F('team2_goals')),
            When(Q(team2=team), then=F('team1_goals')),
            default=Value(0),
            output_field=IntegerField())).aggregate(total_goals=Sum('goals'))['total_goals']

    # Returns the number of games the team has won from the queryset passed in
    def total_games_won(self, queryset, team, apply_update=False):
        if apply_update:
            self.update_fixtures()
        games_won = 0
        for fixture in queryset:
            if fixture.get_winner() == team:
                games_won += 1
        return games_won

    # Returns the number of games the team has drawn from the queryset passed in
    def total_games_drawn(self, queryset, team, apply_update=False):
        if apply_update:
            self.update_fixtures()
        games_drawn = 0
        for fixture in queryset:
            if fixture.is_draw():
                games_drawn += 1
        return games_drawn

    # Returns the number of games the team has lost from the queryset passed in
    def total_games_lost(self, queryset, team, apply_update=False):
        if apply_update:
            self.update_fixtures()
        games_lost = 0
        for fixture in queryset:
            if fixture.get_loser() == team:
                games_lost += 1
        return games_lost