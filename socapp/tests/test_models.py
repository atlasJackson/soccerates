from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q, Count
from django.test import TestCase
from django.utils import timezone
import socapp.tests.test_helpers as helpers

from socapp.models import *
from socapp_auth.models import UserProfile, TournamentPoints


# Tests for the Team model
class TeamTests(TestCase):

    fixtures = ['tournaments.json', 'teams.json', 'games.json']
    
    def setUp(self):
        self.group = "G"
        self.team1 = helpers.generate_team("England", "ENG", self.group)
        self.team2 = helpers.generate_team("Belgium", "BEL", self.group) 
    
    # Tests that the correct number of teams/countries are present in the database
    def test_correct_total_number_of_teams(self):
        NUM_TEAMS = 32
        self.assertEqual(Team.objects.count(), NUM_TEAMS)
    
    def test_team_has_three_group_stage_fixtures(self):
        GROUP_STAGE_FIXTURES = 3
        fixtures = Fixture.objects.filter(
            (Q(team1=self.team1.id) | Q(team2=self.team1.id)) & Q(stage=Fixture.GROUP)
        )
        self.assertEqual(fixtures.count(), GROUP_STAGE_FIXTURES)
    
    def test_team_name_unique_constraint(self):
        with self.assertRaises(IntegrityError):
            Team.objects.create(name="England", group=self.group)

    def test_str_representation(self):
        self.assertEqual("England", str(self.team1))
    
    def test_team_equality(self):
        self.assertEqual(self.team1, self.team1)
        self.assertNotEqual(self.team1, self.team2)
    
    # Test to ensure that groups outwith the range A-H cannot be added to the system
    def test_group_name(self):
        with self.assertRaises(ValidationError):
            self.team1.group = "X"
            self.team1.save()
        with self.assertRaises(ValidationError):
            self.team1.group = 1
            self.team1.save()
            
    def test_there_are_eight_groups(self):
        num_unique_groups = Team.objects.values('group').distinct().count()
        self.assertEqual(num_unique_groups, 8)
    
    # Test to ensure all groups have 4 teams
    def test_each_group_has_four_teams(self):
        group_counts = Team.objects.values('group').annotate(teams_per_group=Count('group'))
        for group in group_counts:
            self.assertEquals(group['teams_per_group'], 4)

    # Tests the Team model's get_fixtures method returns the correct fixtures
    def test_get_fixtures(self):
        fixture_set = self.team1.get_fixtures()
        expected_fixtures = Fixture.objects.select_related('team1', 'team2').filter(Q(team1 = self.team1.id) | Q(team2 = self.team1.id))
        self.assertQuerysetEqual(fixture_set, expected_fixtures, ordered=False, transform=lambda x: x)

    # There are 6 fixtures per group, and this test should verify that
    def test_each_group_has_six_fixtures(self):
        groups = Team.objects.values('group').distinct()
        for group in groups:
            groupname = group['group']
            num_fixtures_in_group = Fixture.objects.select_related('team1', 'team2') \
                .filter(Q(team1__group=groupname)).count()
            self.assertEquals(num_fixtures_in_group, 6)

# Tests for the Fixture model
class FixtureTests(TestCase):
    fixtures = ['tournaments.json', 'teams.json', 'games.json']

    def setUp(self):
        self.group = "G"
        self.team1 = helpers.generate_team("Panama","PAN",self.group)
        self.team2 = helpers.generate_team("England", "ENG", self.group)
        self.fixture = helpers.generate_fixture(self.team1, self.team2, timezone.now())
        self.tournament = Tournament.objects.first()
    
    def test_str_representation(self):
        self.assertEqual("Panama vs England", str(self.fixture))
    
    # Tests that the default match status is set to NOT_STARTED
    def test_default_match_status(self):
        self.assertEquals(self.fixture.status, Fixture.MATCH_STATUS_NOT_PLAYED)
        self.assertFalse(self.fixture.status)
    
    def test_cannot_enter_goals_for_only_one_team_in_fixture(self):
        with self.assertRaises(ValidationError):
            self.fixture.team1_goals = 2
            self.fixture.team2_goals = None
            self.fixture.save()
    
    def test_can_renullify_both_teams_goals_fields(self):
        helpers.play_match(self.fixture, 1,1)
        self.fixture.team1_goals = None
        self.fixture.team2_goals = None
        self.fixture.save()
    
    # Tests the auto-updating of the status field after the result is entered, via the model's save method
    def test_match_status_changes_when_both_teams_have_goals(self):
        self.assertEquals(self.fixture.status, Fixture.MATCH_STATUS_NOT_PLAYED)
        helpers.play_match(self.fixture, 2, 0)
        self.assertEquals(self.fixture.status, Fixture.MATCH_STATUS_PLAYED)

    # Tests the get_group method returns the correct value
    def test_get_group(self):
        self.assertEqual(self.fixture.get_group(), self.group)
        group_name = "B"
        self.assertNotEqual(self.fixture.get_group(), group_name)
        # Test returns None in knockout stages
        self.fixture.stage = Fixture.FINAL
        self.assertIsNone(self.fixture.get_group())

    # Test to ensure the same team cannot be added as both team1 and team2
    def test_prevent_duplicate_teams(self):
        with self.assertRaises(ValidationError):
            helpers.generate_fixture(self.team1, self.team1, timezone.now())
    
    # Tests the logic behind the is_draw method
    def test_is_draw(self):
        self.assertIsNone(self.fixture.is_draw()) # Method should return None if the match hasn't been played
        helpers.play_match(self.fixture, 3, 2) # Play match - not a draw, so the method should return false
        self.assertFalse(self.fixture.is_draw())
        helpers.play_match(self.fixture, 1, 1) # Play match - draw, so the method should return true
        self.assertTrue(self.fixture.is_draw())
        

    # Test to ensure that, if the match is a group stage match, a ValidationError is raised if the teams aren't in the same group
    # Also tests to ensure matches that AREN'T group stage matches do not raise this error.
    def test_teams_in_same_group(self):
        group = "B"
        team = helpers.generate_team(name="Wales", country_code="WAL", group=group)
        
        with self.assertRaises(ValidationError):
            f = helpers.generate_fixture(team1=self.team1, team2=team, match_date=timezone.now())
        
        # Test that the Fixture with teams from different groups can be added if not a group-stage match.
        f = helpers.generate_fixture(team1=self.team1, team2=team, match_date=timezone.now(), stage=Fixture.QUARTER_FINALS)
        self.assertIsNotNone(f.id)

    # Tests that the result available method returns correctly
    def test_result_available(self):
        self.assertFalse(self.fixture.result_available())
        helpers.play_match(self.fixture, 3, 2)
        self.assertTrue(self.fixture.result_available())

    # Tests logic behind get_winner method.
    def test_get_winner(self):
        self.assertIsNone(self.fixture.get_winner()) # Should be None by default, as the match has not happened yet.
        helpers.play_match(self.fixture, 3,2) # team1 wins 3-2
        self.assertEquals(self.team1, self.fixture.get_winner()) # Assert team1 is the winner
        self.fixture.team2_goals = 4 # now team2 is the winner
        self.assertEquals(self.team2, self.fixture.get_winner())

        helpers.play_match(self.fixture, 1,1) # Fixture ends in a draw: should return None
        self.assertIsNone(self.fixture.get_winner())

    # Tests logic behind get_loser method.
    def test_get_loser(self):
        self.assertIsNone(self.fixture.get_loser())
        helpers.play_match(self.fixture, 3,2) # team1 wins 3-2
        self.assertEquals(self.team2, self.fixture.get_loser())
        self.fixture.team2_goals = 4
        self.assertEquals(self.team1, self.fixture.get_loser())

    # Tests the static method on the Fixture model which returns all fixtures in order of their match-date
    def test_all_fixtures_by_date(self):
        fixtures = self.tournament.all_fixtures_by_date()
        
        # Assert that 'fixtures' is ordered:
        sorted = True # Flag: changed within the for-loop below if the result is NOT in sorted order
        num_fixtures = len(fixtures)
        for i in range(1, num_fixtures):
            if fixtures[i-1].match_date > fixtures[i].match_date:
                sorted = False
                break
        
        self.assertTrue(sorted)

    # Tests the static method on the Fixture model which returns all fixtures in belonging to a particular stage, ex: group, quarter-final
    def test_all_fixtures_by_stage(self):
        """ All fixtures seeded in the Django fixtures JSON files are group stage games.
            We make one fixture a latter-stage match here for testing purposes """
        
        Fixture.objects.filter(pk=1).update(stage=Fixture.ROUND_OF_16)

        # Now, grab the group stage fixtures
        fixtures = Fixture.all_fixtures_by_stage(Fixture.GROUP)
        correct_stage = True
        for fixture in fixtures:
            if not fixture.stage == Fixture.GROUP:
                correct_stage = False
                break
        self.assertTrue(correct_stage)

        # Test for the last-16 fixtures - there should be one (created above), with a PK of 1
        fixtures = Fixture.all_fixtures_by_stage(Fixture.ROUND_OF_16)
        self.assertEqual(len(fixtures), 1)
        self.assertIn(Fixture.objects.get(pk=1), fixtures)

    # Tests the method that gets all the WC fixtures that have been played thus far
    def test_all_completed_fixtures(self):
        tournament = Tournament.objects.first()
        # By default, no games are completed. Here, we set 2 games to completed, and test the method.
        Fixture.objects.filter(pk__in=[1,2]).update(status=Fixture.MATCH_STATUS_PLAYED)
        
        completed_fixtures = tournament.all_completed_fixtures()
        self.assertEqual(completed_fixtures.count(), 2)
        self.assertQuerysetEqual(Fixture.objects.select_related('team1', 'team2').filter(
            pk__in=[1,2]), completed_fixtures, ordered=False, transform=lambda x: x
        )

    # Tests the Fixture model's get_fixtures_by_group method, to ensure the correct Fixtures are returned
    # Group A teams are: Russia, Saudi Arabia, Egypt, Uruguay
    def test_all_fixtures_by_group(self):
        fixtures = Fixture.all_fixtures_by_group("A")
        expected_teams = Team.objects.filter(group="A")
        expected_fixtures = Fixture.objects.select_related('team1','team2').filter(team1__in=expected_teams)
        self.assertQuerysetEqual(fixtures, expected_fixtures, ordered=False, transform=lambda x: x)

        # Assert the list matches expected values
        expected = ["Russia", "Saudi Arabia", "Egypt", "Uruguay"]
        team_names = list(expected_teams.values_list('name', flat=True))
        self.assertEquals(team_names, expected)

        # Check that if an invalid group is passed as a parameter, a ValidationError is raised
        with self.assertRaises(ValidationError):
            fixtures = Fixture.all_fixtures_by_group("X")
        
    # Big test: ensures that when a result is entered, the changes in the Fixture model propagate to the Team model.
    # For example: entering a value for team1_goals in the Fixture should automatically increment the associated team's goals_for field.
    def test_fixture_changes_correctly_update_team_model(self):
        self.assertIsNone(self.fixture.team1_goals)
        self.assertIsNone(self.fixture.team1_goals)
        TEAM1_GOALS, TEAM2_GOALS = 2, 1
        helpers.play_match(self.fixture, TEAM1_GOALS, TEAM2_GOALS) # Team1 wins 2-1
        # Now we check that updating the fixture with a result has the correct knock-on effect to the Team models
        self.assertEquals(self.fixture.team1.games_played, 1)
        self.assertEquals(self.fixture.team1.goals_for, 2)
        self.assertEquals(self.fixture.team1.goals_against, 1)
        self.assertEquals(self.fixture.team2.goals_for, 1)
        self.assertEquals(self.fixture.team2.goals_against, 2)
        self.assertEquals(self.fixture.team1.games_won, 1)
        self.assertEquals(self.fixture.team2.games_lost,1)
        self.assertEquals(self.fixture.team1.games_drawn, 0)
        self.assertEquals(self.fixture.team2.games_drawn, 0)

        # Edit the fixture and check the changes correctly propagate to the Team models
        TEAM1_GOALS, TEAM2_GOALS = 3, 0
        helpers.play_match(self.fixture, TEAM1_GOALS, TEAM2_GOALS) # Team1 wins 3-0
        self.assertEquals(self.fixture.team1.games_played, 1)
        self.assertEquals(self.fixture.team1.goals_for, 3)
        self.assertEquals(self.fixture.team1.goals_against, 0)
        self.assertEquals(self.fixture.team2.goals_for, 0)
        self.assertEquals(self.fixture.team2.goals_against, 3)
        self.assertEquals(self.fixture.team1.games_won, 1)
        self.assertEquals(self.fixture.team2.games_lost,1)
        self.assertEquals(self.fixture.team1.games_drawn, 0)
        self.assertEquals(self.fixture.team2.games_drawn, 0)

        # Check that the result changing correctly affects all fields
        TEAM1_GOALS, TEAM2_GOALS = 1, 1
        helpers.play_match(self.fixture, TEAM1_GOALS, TEAM2_GOALS) # 1-1
        self.assertEquals(self.fixture.team1.games_played, 1)
        self.assertEquals(self.fixture.team1.goals_for, 1)
        self.assertEquals(self.fixture.team1.goals_against, 1)
        self.assertEquals(self.fixture.team2.goals_for, 1)
        self.assertEquals(self.fixture.team2.goals_against, 1)
        self.assertEquals(self.fixture.team1.games_won, 0)
        self.assertEquals(self.fixture.team2.games_lost,0)
        self.assertEquals(self.fixture.team1.games_drawn, 1)
        self.assertEquals(self.fixture.team2.games_drawn, 1)

    def test_removing_result_propagates_to_related_teams(self):
        TEAM1_GOALS, TEAM2_GOALS = 2,2
        helpers.play_match(self.fixture, TEAM1_GOALS, TEAM2_GOALS)
        self.assertIsNotNone(self.fixture.team1_goals)
        # Reset the goals fields to None and save
        self.fixture.team1_goals = None
        self.fixture.team2_goals = None
        self.fixture.save()
        # Check to ensure the Team model fields are all reset to 0
        self.assertEquals(self.fixture.team1.games_played, 0)
        self.assertEquals(self.fixture.team1.goals_for, 0)
        self.assertEquals(self.fixture.team1.goals_against, 0)
        self.assertEquals(self.fixture.team2.goals_for, 0)
        self.assertEquals(self.fixture.team2.goals_against, 0)
        self.assertEquals(self.fixture.team1.games_won, 0)
        self.assertEquals(self.fixture.team2.games_lost,0)
        self.assertEquals(self.fixture.team1.games_drawn, 0)
        self.assertEquals(self.fixture.team2.games_drawn, 0)

class UserProfileTests(TestCase):
    def setUp(self):
        self.user = helpers.generate_user()
        self.tournament = Tournament.objects.first()

    # Queries the m2m table storing user points per tournament
    def tournament_pts(self):
        return self.user.profile.tournament_pts.filter(tournament=self.tournament).get().points

    # Tests to ensure a UserProfile is also created whenever a user is created
    def test_userprofile_creation(self):
        self.assertIsInstance(self.user.profile, UserProfile)
    
    # Tests that users have zero points upon creation
    def test_user_starts_with_zero_points(self):
        self.assertEquals(self.user.profile.points, 0)
        with self.assertRaises(TournamentPoints.DoesNotExist):
            self.assertEquals(self.tournament_pts(), 0)

class AnswerTests(TestCase):
    fixtures = ['tournaments.json', 'teams.json', 'games.json']
    
    def setUp(self):
        self.user = helpers.generate_user()
        self.fixture = Fixture.objects.get(pk=1)

    # Tests the unique_together constraint, to ensure a user can only have 1 answer for a given fixture
    def test_user_cannot_add_more_than_one_answer_per_match(self):
        a = helpers.generate_answer(self.user, self.fixture)
        self.assertIsInstance(a, Answer)
        with self.assertRaises(IntegrityError):
            a = helpers.generate_answer(self.user, self.fixture)
    
    def test_user_can_update_their_answer(self):
        a = helpers.generate_answer(self.user, self.fixture)
        a.team1_goals = 4
        a.save()
        self.assertEquals(Answer.objects.get(pk=a.id).team1_goals, 4)

    def test_team_goals_fields_cannot_be_null(self):
        a = helpers.generate_answer(self.user, self.fixture)
        a.team1_goals = None
        a.save()
        self.assertEquals(a.team1_goals, 0)


# Tests for the Group model
#class GroupTests(TestCase):
    
    # Test unique constraint on group name (important, as we should not have 2 groups with the same name in the DB)
    # def test_group_name_is_unique(self):
    #     with self.assertRaises(IntegrityError):
    #         Group.objects.create(name="A")
        
    # Tests the Group model's get_teams method, to ensure the correct Teams are returned
    # Group 1 teams are: Russia, Saudi Arabia, Egypt, Uruguay
    # def test_get_teams(self):
    #     team_set = self.group1.get_teams()
    #     expected_teams = Team.objects.filter(group = self.group1.id)
    #     self.assertQuerysetEqual(team_set, expected_teams, ordered=False, transform=lambda x: x)

    #     # Assert the list matches expected values
    #     expected = ["Russia", "Saudi Arabia", "Egypt", "Uruguay"]
    #     team_names = list(team_set.values_list('name', flat=True))
    #     self.assertEquals(team_names, expected)