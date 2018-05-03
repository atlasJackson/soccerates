from socapp.models import *


def generate_group(name):
    group = Group.objects.get_or_create(name=name)[0]
    return group

def generate_team(name, country_code, group):
    team = Team.objects.get_or_create(name=name, group=group)[0]
    team.country_code = country_code
    team.save()
    return team

def generate_fixture(team1, team2, match_date, stage=1):
    fixture = Fixture.objects.get_or_create(team1=team1, team2=team2, match_date=match_date, stage=stage)[0]
    return fixture

# Simulates the changes to the Fixture model upon the match being played
def play_match(fixture, team1_goals, team2_goals):
    fixture.status = Fixture.MATCH_STATUS_PLAYED
    fixture.team1_goals = team1_goals
    fixture.team2_goals = team2_goals
    fixture.save()