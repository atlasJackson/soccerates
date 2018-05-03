# Models to store data for import to application database.
from datetime import datetime

class Fixture:
	def __init__(self, team1, team2, kickoff_time, match_date):
		self.team1 = team1
		self.team2 = team2
		self.kickoff_time = kickoff_time
		self.match_date = match_date

	# Return list of both teams in the fixture
	def get_teams(self):
		return [self.team1, self.team2]

	# Dates to be stored in the database in the form: YYYY-MM-DD
	# May need a function to map backwards
	def convert_date_to_ISO(self):
		# Rework date
		date = self.match_date.split()
		date = "{} {} {}".format(date[1][:-2], date[2], date[3]) #Removes day of week (ie-"Monday") and removes day suffix (ie - "st" from 1st) from date

		return datetime.strptime(date, '%d %B %Y').date() # Convert to ISO repr

	def __str__(self):
		return "{} v {} ({} {})".format(self.team1, self.team2, self.match_date, self.kickoff_time)

	# Defines whether two fixture instances are equal.
	# If both fixtures have the same teams, and the same match-date and kickoff-time, then the fixtures are equal
	def __eq__(self, other):
		assert isinstance(other, Fixture)
		for team in self.get_teams():
			if team in other.get_teams():
				continue
			else:
				return False
		if self.kickoff_time == other.kickoff_time and self.match_date == other.match_date:
			return True
		return False


class Team:
	def __init__(self, name, group=None):
		self.name = name
		self.group = self.group_name(group) # Helper function: checks group name is valid

	def assign_to_group(self, group):
		self.group = self.group_name(group)

	def group_name(self, group):
		if group:
			if len(group) == 1:
				return group.upper()
			else:
				print("Invalid group name")
		return None


	def __str__(self):
		if self.group:
			return "{} (Group {})".format(self.name, self.group)
		else:
			return self.name

	# Simplest equality test: if the names match, it's the same Team
	def __eq__(self, other):
		return self.name == other.name


class Group:
	def __init__(self, group_name, team1, team2, team3, team4):
		self.fixtures = []
		self.group_name = group_name
		self.team1 = team1
		self.team2 = team2
		self.team3 = team3
		self.team4 = team4

	def add_fixture(self, fixture):

		# Check fixture.team1 and team2 are in this group
		for team in fixture.get_teams():
			if not self.is_team_in_group(team):
				print("Cannot add this fixture: {} is not listed in this group".format(team))
				return

		# Check fixture hasn't already been added
		if self.check_fixture_exists(fixture):
			print ("This fixture - {} - has already been added to this group".format(fixture))
			return

		# If this is reached, the fixture can be added to the group
		self.fixtures.append(fixture)

	def fixture_list(self):
		if self.fixtures:
			return self.fixtures

	def get_teams_as_list(self):
		return [self.team1, self.team2, self.team3, self.team4]

	# Asserts whether or not a team is in this group instance
	def is_team_in_group(self, team):
		return team in self.get_teams_as_list()

	# Check to ensure that the fixture the client is attempting to add has not already been added
	def check_fixture_exists(self, fixture):
		for existing_fixture in self.fixtures:
			if existing_fixture == fixture:
				return True
		return False

	def __str__(self):
		return 'Group {}: {}, {}, {}, {}'.format(self.group_name, self.team1.name, self.team2.name, self.team3.name, self.team4.name)