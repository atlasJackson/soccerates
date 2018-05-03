from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
import socapp.tests.test_helpers as helpers

from socapp.models import *


# Tests for the Team model
class TeamTests(TestCase):

    def setUp(self):
        self.group = helpers.generate_group("A")
        self.team1 = helpers.generate_team("Scotland", "SCO", self.group)
        self.team2 = helpers.generate_team("England", "ENG", self.group)

    def test_str_representation(self):
        self.assertEqual("Scotland", str(self.team1))
    
    def test_team_equality(self):
        self.assertEqual(self.team1, self.team1)
        self.assertNotEqual(self.team1, self.team2)

# Tests for the Group model
class GroupTests(TestCase):
    def setUp(self):
        self.group1 = helpers.generate_group("A")

    # Test the class's string representation
    def test_str_representation(self):
        self.assertEqual("Group A", str(self.group1))
    
    # Test the definition of equality between two Group instances
    def test_group_equality(self):
        team = helpers.generate_team("Scotland", "SCO", self.group1)
        group2 = helpers.generate_group("B")
        group3 = helpers.generate_group("A")
        self.assertNotEqual(self.group1, team)
        self.assertNotEqual(self.group1, group2)
        self.assertEqual(self.group1, group3)

    # Test to ensure that groups outwith the range A-H cannot be added to the system
    def test_group_name(self):
        with self.assertRaises(ValidationError):
            g = helpers.generate_group("X")
        with self.assertRaises(ValidationError):
            g = helpers.generate_group(1)
        
        h = helpers.generate_group("A")
        self.assertIsNotNone(h.id)

# Tests for the Fixture model
class FixtureTest(TestCase):
    def setUp(self):
        self.group = helpers.generate_group("A")
        self.team1 = helpers.generate_team("Scotland","SCO",self.group)
        self.team2 = helpers.generate_team("England", "ENG", self.group)
        self.fixture = helpers.generate_fixture(self.team1, self.team2, timezone.now())
    
    def test_str_representation(self):
        self.assertEqual("Scotland vs England", str(self.fixture))
    
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
        g = helpers.generate_group("B")
        self.assertNotEqual(self.fixture.get_group(), g)

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
        group = helpers.generate_group(name="B")
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


    