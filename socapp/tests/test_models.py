from django.test import TestCase
import socapp.tests.test_helpers as helpers

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

    def test_str_representation(self):
        self.assertEqual("Group A", str(self.group1))
    
    def test_group_equality(self):
        team = helpers.generate_team("Scotland", "SCO", self.group1)
        self.assertNotEqual(self.group1, team)
