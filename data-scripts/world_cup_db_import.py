import psycopg2
from settings import database_settings #Settings omitted from online repository for security reasons
from world_cup_data import groups, teams, fixtures
from world_cup_data_models import Team, Fixture, Group

### Script that imports model data to PostgreSQL database

NUMBER_OF_GROUPS = 8
NUMBER_OF_TEAMS = 32
NUMBER_OF_FIXTURES = 48

# Initiate database connection, and get cursor object
def init_and_get_cursor():
	conn_str = ""
	for k,v in database_settings.items():
		conn_str += "{}={} ".format(k,v)

	print ("Connecting...")
	conn = psycopg2.connect(conn_str)

	conn.autocommit = True
	print ("Connected!")
	return conn.cursor()

# Tables created via pgAdmin. Below are table-insert functions, which transform names to keys where necessary

"""
'group' table schema (subject to change):

id - autoincrementing integer field
name - character field

Additional params for qualifiers and group data may be added later
"""
def insert_groups(cursor):
	for group in groups:		
		insert_str = "INSERT INTO groups (name) VALUES (%s);"
		cursor.execute(insert_str, group.group_name)

	# Check all 8 groups have been entered into the table
	if count_check(cursor, "SELECT Count(*) FROM groups", NUMBER_OF_GROUPS):
		print("Group data has now been entered successfully")
	else:
		print("Error entering group data")


"""
'team' table schema (subject to change):

id - autoincrementing integer field
name - varchar field
group_id = integer field, foreign key references group(id)

Group id must be populated based on a lookup to the 'group' table
"""
def insert_teams(cursor):
	for team in teams:
		insert_str = "INSERT INTO teams (name, group_id) VALUES (%s, %s);"
		group_id = get_group(cursor, team.group) # Perform lookup to get the group_id
		cursor.execute(insert_str, (team.name, group_id))

	# Check all 32 teams have been entered into the table
	if count_check(cursor, "SELECT Count(*) FROM teams", NUMBER_OF_TEAMS):
		print("Team data has now been entered successfully")
	else:
		print("Error entering team data")		


"""
'fixtures table schema (subject to change)'

id - autoincrementing integer field
team1 - integer field, foreign key references team(id)
team2 - integer field, foreign key references team(id)
kickoff_time - time field
match_date - date field
group_id - integer field, foreign key references group(id)

"""
def insert_fixtures(cursor):
	for fixture in fixtures:
		team1 = fixture.team1
		team2 = fixture.team2
		kickoff_time = fixture.kickoff_time
		match_date = fixture.convert_date_to_ISO() #Convert for database
		group_id = get_group(cursor, team1.group)
		team1_id = get_team(cursor, team1.name)
		team2_id = get_team(cursor, team2.name)

		assert team1_id is not team2_id # Basic test
		
		# Build query and execute:
		insert_str = """
			INSERT INTO fixtures (team_a, team_b, kickoff_time, match_date, group_id)
			VALUES (%s, %s, %s, %s, %s);"""
		cursor.execute(insert_str, [team1_id, team2_id, kickoff_time, match_date, group_id])

	if count_check(cursor, "SELECT Count(*) FROM fixtures", NUMBER_OF_FIXTURES):
		print ("Fixture data has been entered successfully")
	else:
		print("Error entering fixture data")



### HELPER FUNCTIONS ###

# Checks if data is entered: 'query' should have form SELECT COUNT(*) FROM tablename. 'expected_number' is an integer representing the expected query result
def count_check(cursor, query, expected_number):
	cursor.execute(query)
	count = cursor.fetchone()[0]
	if count is expected_number:
		return True
	return False

# Maps a team's group name to the group ID
def get_group(cursor, group_name):
	query_str = "SELECT id FROM groups WHERE name = %s;"
	cursor.execute(query_str, str(group_name))
	result = cursor.fetchone()[0]
	return result

# Maps a team's group name to the group ID
def get_team(cursor, team_name):
	query_str = "SELECT id FROM teams WHERE name = %s;"
	cursor.execute(query_str, [team_name])
	result = cursor.fetchone()[0]
	return result



# Script entry point...
def main():

	# Get the cursor
	cursor = init_and_get_cursor()

	# Enter groups into the database if not already done
	if not count_check(cursor, "SELECT Count(*) FROM groups", NUMBER_OF_GROUPS):
		insert_groups(cursor)
	else:
		print("Group data already entered")

	# Enter teams to the database if not already done
	if not count_check(cursor, "SELECT Count(*) FROM teams", NUMBER_OF_TEAMS):
		insert_teams(cursor)
	else:
		print("Team data already entered")

	# Enter fixtures to the database if not already done
	if not count_check(cursor, "SELECT Count(*) FROM fixtures", NUMBER_OF_FIXTURES):
		insert_fixtures(cursor)
	else:
		print("Fixture data already entered")

if __name__ == "__main__":
	main()


"""
SAMPLE DATABASE QUERIES:

1. Get all fixtures:
SELECT t1.name, t2.name, f.kickoff_time, f.match_date, g.name FROM fixtures f 
JOIN teams AS t1 ON f.team_a = t1.id 
JOIN teams AS t2 ON f.team_b = t2.id
JOIN groups AS g ON f.group_id = g.id
ORDER BY f.match_date, kickoff_time

2. All teams and their groups:
SELECT t.name, g.name FROM teams t
JOIN groups g ON t.group_id = g.id

