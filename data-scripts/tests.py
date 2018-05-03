# Tests file - tests model entity functions
# Run all tests with below command:
#   python -m unittest tests

import unittest
from world_cup_data_models import *

# Team class tests
class TeamTestCase(unittest.TestCase):

	# Set up team objects for testing
	def setUp(self):
		self.team1 = Team("Scotland") #Team with no group
		self.team2 = Team("England", 'B') # Team with group

	def tearDown(self):
		self.team1 = None
		self.team2 = None

	# Tests the team entity's group functionality.
	def test_team_has_group(self):
		self.assertEqual(self.team2.group, 'B')
		self.assertEqual(self.team1.group, None) # Team not assigned group yet
		self.team1.assign_to_group('F') # Assign group
		self.assertEqual(self.team1.group, 'F') # Check again

		#Check lowercase group name is converted to uppercase:
		self.team1.assign_to_group("c")
		self.assertEqual(self.team1.group, "C")

		# Check invalid group name (ie - more than 1 character) is not accepted
		self.team1.assign_to_group("abcdef")
		self.assertEqual(self.team1.group, None)

	# Tests "__eq__" class function that defines team equality
	def test_team_equality(self):
		self.assertNotEqual(self.team1, self.team2)
		self.team2 = Team("Scotland")
		self.assertEqual(self.team1, self.team2)


class FixtureTestCase(unittest.TestCase):

	# Set up Fixture objects
	def setUp(self):
		self.fixture1 = Fixture(Team("Scotland"), Team("England"), "15:00", "Monday 4th July")
		self.fixture2 = Fixture(Team("Rangers"), Team("Celtic"), "16:00", "Wednesday 6th July")

	def tearDown(self):
		self.fixture1 = None
		self.fixture2 = None

	# Tests the method that returns the teams involved in the fixture (called 'get_teams')
	def test_get_teams_as_list(self):
		correctTeams = [Team("Scotland"), Team("England")]
		incorrectTeams = [Team("Wales"), Team("Ireland")]

		self.assertEqual(self.fixture1.get_teams(), correctTeams)
		self.assertNotEqual(self.fixture1.get_teams(), incorrectTeams)

		# Length should always be 2
		teamCount = len(self.fixture1.get_teams())
		bothValid = len(self.fixture1.get_teams()) == len(self.fixture2.get_teams())
		self.assertEqual(teamCount, 2)
		self.assertTrue(bothValid)




	# Tests "__eq__" class function that defines team equality
	def test_fixture_equality(self):
		self.assertNotEqual(self.fixture1, self.fixture2)

		# Same teams, but different date: should still not be equal
		self.fixture2 = Fixture(Team("Scotland"), Team("England"), "15:00", "Tuesday 5th July")
		self.assertNotEqual(self.fixture1, self.fixture2)

		# Same teams, same date: should now be equal
		self.fixture2 = Fixture(Team("Scotland"), Team("England"), "15:00", "Monday 4th July")
		self.assertEqual(self.fixture1, self.fixture2)