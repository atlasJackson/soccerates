# Gather data relating to teams, groups and fixtures, and prepare for database entry.
# Scraped from "http://www.bbc.co.uk/sport/football/world-cup/schedule/group-stage" using BeautifulSoup4 library 

import requests
from bs4 import BeautifulSoup, Tag
from world_cup_data_models import Fixture, Team, Group


### Parsing functions ###

# Parse the HTML to get the Group Stage fixtures and their dates
def get_all_fixtures(soup):
	fixtures = []
	for tags in soup.find_all(class_='fixture__wrapper'):
		this_fixture = {} # Hold fixture details in this dict
		for tag in tags:
			if isinstance(tag, Tag):
				tag = str.strip(tag.text)

				# Check if 'tag' contains a number, if so it's the kickoff time, not a country
				if any(i.isdigit() for i in tag):
					this_fixture['kickoff_time'] = tag
				else:
					team = Team(tag)
					if not 'team1' in this_fixture:
						this_fixture['team1'] = team
					else:
						this_fixture['team2'] = team
		if not 'match_date' in this_fixture:
			this_fixture['match_date'] = tags.parent.h3.text + ' 2018' # Append year, since the webpage does not display this.

		# With the data in place, create the Fixture instance from the dictionary, and add to the 'fixtures' list
		fixtures.append(Fixture(**this_fixture))
	return fixtures


# Using the fixtures,and the knowledge that there are 6 fixtures per group, partition the fixtures into their respective groups
def create_groups(fixtures):
	counter = 0 # Control variable
	all_groups = [] # List of lists: inner lists will represent individual groups
	this_group = []
	group_name = 'A'

	for fixture in fixtures:
		# Assign teams in each fixture to appropriate group
		[team.assign_to_group(group_name) for team in fixture.get_teams()]

		# If length of group is 4, this group is complete. Modulo 6 == 0 will get next group's batch of fixtures, given that there are 6 games per group
		if len(this_group) == 4:
			counter += 1
			if counter % 6 == 0:
				# When this condition is met, we have reached a new group's fixtures.
				# Add the existing group to the 'groups' list, and clear 'this_group' for the next group. Increment group_name for next group.
				all_groups.append(Group(group_name, *this_group))
				this_group = []
				group_name = chr(ord(group_name) + 1) # Increment group_name, e.g: 'A' becomes 'B', 'B' becomes 'C', etc
		else:
			# Here, there are NOT 4 teams in the group, so there are still teams to add. Check each fixture, and if any team is NOT in the group already, add them
			team1 = fixture.team1
			team2 = fixture.team2
			if not team1 in this_group:
				this_group.append(team1)
			if not team2 in this_group:
				this_group.append(team2)
			counter += 1
	
	return all_groups

def get_all_teams(groups):
	# Groups parameter is a list of all the groups. Individual groups are sublists within this main list.
	teams = []
	for group in groups:
		[teams.append(team) for team in group.get_teams_as_list()]
	return teams


# Each group consists of 6 fixtures
def add_fixtures_to_group(groups, fixtures):
	fixture_count = 0
	group_index = 0
	for fixture in fixtures:
		groups[group_index].add_fixture(fixture)
		fixture_count += 1
		if fixture_count % 6 == 0:
			group_index += 1


# Script processing workflow defined here:
def main():
	# Perform the web request to get the world cup data
	try:
		response = requests.get('http://www.bbc.co.uk/sport/football/world-cup/schedule/group-stage')
	except requests.exceptions.RequestException as e:
		print(e)
		sys.exit(1)

	response = response.text # Transform the Response object to HTML text
	soup = BeautifulSoup(response, 'html.parser') # Pass the HTML response text to the BeautifulSoup object for parsing

	# Define collection variables. These are global to allow import to the database processing script
	global fixtures, groups, teams

	# Populate collection variables
	fixtures = get_all_fixtures(soup)
	groups = create_groups(fixtures)
	teams = get_all_teams(groups)

	# Rudimentary tests to confirm the correct amount of data is in place:
	assert len(teams) == 32 		# 32 teams in world cup
	assert len(fixtures) == 48		# 48 group stage fixtures
	assert len(groups) == 8			# 8 groups

	# Test no fixture discrepancies (ie: two teams from different groups playing one another):
	for fixture in fixtures:
		assert fixture.team1.group == fixture.team2.group

	# At this point, group objects exist without fixtures: the fixtures are added via this function
	add_fixtures_to_group(groups, fixtures)

# Call workflow function
main()

# Write data out to text file
"""
with open('world_cup.txt', 'w') as f:
	for group in groups:
		f.write(str(group) + "\n")

	f.write("\n")

	for fixture in fixtures:
		f.write(str(fixture) + "\n")
"""