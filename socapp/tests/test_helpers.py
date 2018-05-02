from socapp.models import *


def generate_group(name):
    group = Group.objects.get_or_create(name=name)[0]
    return group

def generate_team(name, country_code, group):
    team = Team.objects.get_or_create(name=name, group=group)[0]
    team.country_code = country_code
    team.save()
    return team

def generate_fixture(team1, team2, match_date):
    fixture = Fixture.objects.get_or_create(team1=team1, team2=team2, match_date=match_date)[0]
    return fixture