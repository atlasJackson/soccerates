from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.db.models import Q, Count
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
import socapp.tests.test_helpers as helpers

from socapp.models import *


# Tests for the Team model
class TeamTests(TestCase):

    fixtures = ['teams.json', 'games.json']
    
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
    fixtures = ['teams.json', 'games.json']

    def setUp(self):
        self.group = "G"
        self.team1 = helpers.generate_team("Panama","PAN",self.group)
        self.team2 = helpers.generate_team("England", "ENG", self.group)
        self.fixture = helpers.generate_fixture(self.team1, self.team2, timezone.now())
    
    def test_str_representation(self):
        self.assertEqual("Panama vs England", str(self.fixture))
    
    # Tests that the default match status is set to NOT_STARTED
    def test_default_match_status(self):
        self.assertEquals(self.fixture.status, Fixture.MATCH_STATUS_NOT_PLAYED)
        self.assertFalse(self.fixture.status)
    
    # Test the status after changing: potentially, this may work by comparing the current date to the match-date in future
    def test_match_status(self):
        self.fixture.status = Fixture.MATCH_STATUS_PLAYED
        self.assertEquals(self.fixture.status, Fixture.MATCH_STATUS_PLAYED)
        self.assertTrue(self.fixture.status)

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
            f = helpers.generate_fixture(self.team1, self.team1, timezone.now())
    
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

    # Tests get_winner method.
    def test_get_winner(self):
        self.assertIsNone(self.fixture.get_winner()) # Should be None by default, as the match has not happened yet.
        helpers.play_match(self.fixture, 3,2) # team1 wins 3-2
        self.assertEquals(self.team1, self.fixture.get_winner()) # Assert team1 is the winner
        self.fixture.team2_goals = 4 # now team2 is the winner
        self.assertEquals(self.team2, self.fixture.get_winner())

        helpers.play_match(self.fixture, 1,1) # Fixture ends in a draw: should return None
        self.assertIsNone(self.fixture.get_winner())

    # Tests the static method on the Fixture model which returns all fixtures in order of their match-date
    def test_all_fixtures_by_date(self):
        fixtures = Fixture.all_fixtures_by_date()
        
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
        
        Fixture.objects.filter(pk=1).update(stage=Fixture.LAST_16)

        # Now, grab the group stage fixtures
        fixtures = Fixture.all_fixtures_by_stage(Fixture.GROUP)
        correct_stage = True
        for fixture in fixtures:
            if not fixture.stage == Fixture.GROUP:
                correct_stage = False
                break
        self.assertTrue(correct_stage)

        # Test for the last-16 fixtures - there should be one (created above), with a PK of 1
        fixtures = Fixture.all_fixtures_by_stage(Fixture.LAST_16)
        self.assertEqual(len(fixtures), 1)
        self.assertIn(Fixture.objects.get(pk=1), fixtures)

    # Tests the method that gets all the WC fixtures that have been played thus far
    def test_all_completed_fixtures(self):
        """ By default, no games are completed. Here, we set 2 games to completed, and test the method. """
        Fixture.objects.filter(pk__in=[1,2]).update(status=Fixture.MATCH_STATUS_PLAYED)
        
        completed_fixtures = Fixture.all_completed_fixtures()
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

class UserProfileTests(TestCase):
    def setUp(self):
        self.user = helpers.generate_user()

    # Tests to ensure a UserProfile is also created whenever a user is created
    def test_userprofile_creation(self):
        self.assertIsInstance(self.user.profile, UserProfile)
    
    # Tests that users have zero points upon creation
    def test_user_starts_with_zero_points(self):
        self.assertEquals(self.user.profile.points, 0)

class AnswerTests(TestCase):
    fixtures = ['teams.json', 'games.json']
    
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