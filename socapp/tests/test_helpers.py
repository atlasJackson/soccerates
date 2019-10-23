from django.contrib.auth import get_user_model
from socapp.models import *


def generate_team(name, short_code, group):
    team = Team.objects.get_or_create(name=name, group=group)[0]
    team.short_code = short_code
    team.save()
    return team

def generate_fixture(team1, team2, match_date, stage=Fixture.GROUP):
    tournament = Tournament.objects.first()
    fixture = Fixture.objects.get_or_create(team1=team1, team2=team2, tournament=tournament, match_date=match_date, stage=stage)[0]
    return fixture

def generate_answer(user, fixture, team1_goals=1, team2_goals=1):
    answer = Answer.objects.create(user=user,fixture=fixture, team1_goals=team1_goals, team2_goals=team2_goals)
    return answer

def generate_user(username="test", password="password"):
    User = get_user_model()
    return User.objects.create_user(username=username, password=password)

# Simulates the changes to the Fixture model upon the match being played
def play_match(fixture, team1_goals, team2_goals):
    fixture.team1_goals = team1_goals
    fixture.team2_goals = team2_goals
    fixture.save()